%define _prefix /opt/trafficserver

# https://fedoraproject.org/wiki/Packaging:Guidelines#PIE
%define _hardened_build 1

Summary:	Fast, scalable and extensible HTTP/1.1 compliant caching proxy server
Name:		trafficserver
Version:	7.1.0
Release:	1%{?dist}
License:	ASL 2.0
Group:		System Environment/Daemons
URL:		http://trafficserver.apache.org/index.html

Source0:	http://archive.apache.org/dist/%{name}/%{name}-%{version}.tar.bz2
Source1:	http://archive.apache.org/dist/%{name}/%{name}-%{version}.tar.bz2.asc
Source2:	trafficserver.keyring
Source3:	trafficserver.sysconf
Source4:	trafficserver.service
Source5:	trafficserver.tmpfilesd
Patch1:		trafficserver-init_scripts.patch

Patch101:	trafficserver-6.2.0-require-s-maxage.patch
Patch102:	trafficserver-6.2.0.return_stale_cache_with_s_maxage.patch

# BuildRoot is only needed for EPEL5:
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
# fails on ARMv7 atm (needs investigation), s390 unsupported
ExcludeArch:	%{arm} s390 s390x

BuildRequires:	boost-devel
BuildRequires:	gcc-c++
BuildRequires:	gnupg
BuildRequires:	hwloc-devel
BuildRequires:	openssl-devel
BuildRequires:	pcre-devel
BuildRequires:	perl-ExtUtils-MakeMaker
BuildRequires:	tcl-devel
BuildRequires:	zlib-devel
BuildRequires:	xz-devel
BuildRequires:	autoconf automake libtool

Requires: initscripts
%if %{?fedora}0 > 140 || %{?rhel}0 > 60
# For systemd.macros
BuildRequires: systemd
Requires: systemd
Requires(postun): systemd
%else
Requires(post): chkconfig
Requires(preun): chkconfig initscripts
Requires(postun): initscripts
%endif

%description
Apache Traffic Server is a fast, scalable and extensible HTTP/1.1 compliant
caching proxy server.

%package devel
Summary: Apache Traffic Server development libraries and header files
Group: Development/Libraries
Requires: trafficserver = %{version}-%{release}

%description devel
The trafficserver-devel package include plug-in development libraries and
header files, and Apache httpd style module build system.

%package perl
Summary: Apache Traffic Server bindings for perl
Group: Development/Libraries
Requires: trafficserver = %{version}-%{release}

%description perl
The trafficserver-perl package contains perl bindings.

%prep
#gpgv --homedir /tmp --keyring %{SOURCE2} --status-fd=1 %{SOURCE1} %{SOURCE0} | grep -q '^\[GNUPG:\] GOODSIG'

%setup -q

%patch1 -p1 -b .init
%patch101 -p1
%patch102 -p1

%build
NOCONFIGURE=1 autoreconf -vif
%configure \
  --enable-layout=opt \
  --sysconfdir=%{_prefix}%{_sysconfdir} \
  --localstatedir=%{_prefix}%{_localstatedir} \
  --libexecdir=%{_prefix}/%{_lib}/plugins \
  --with-tcl=/usr/%{_lib} \
  --with-user=ats --with-group=ats \
  --disable-silent-rules \
  --enable-experimental-plugins

make %{?_smp_mflags} V=1

%install
rm -rf %{buildroot}
make DESTDIR=%{buildroot} install

# Remove duplicate man-pages:
rm -rf %{buildroot}%{_docdir}/trafficserver

mkdir -p %{buildroot}%{_sysconfdir}/sysconfig
install -m 644 -p %{SOURCE3} \
   %{buildroot}%{_sysconfdir}/sysconfig/trafficserver

%if %{?fedora}0 > 140 || %{?rhel}0 > 60
install -D -m 0644 -p %{SOURCE4} \
   %{buildroot}/lib/systemd/system/trafficserver.service
install -D -m 0644 -p %{SOURCE5} \
   %{buildroot}%{_sysconfdir}/tmpfiles.d/trafficserver.conf
%else
mkdir -p %{buildroot}/etc/init.d/
mv %{buildroot}%{_prefix}/bin/trafficserver %{buildroot}/etc/init.d
%endif

# Remove libtool archives and static libs
find %{buildroot} -type f -name "*.la" -delete
find %{buildroot} -type f -name "*.a" -delete

rm -f %{buildroot}/%{_prefix}/lib/perl5/x86_64-linux-thread-multi/perllocal.pod
rm -f %{buildroot}/%{_prefix}/lib/perl5/x86_64-linux-thread-multi/auto/Apache/TS/.packlist

#
perl -pi -e 's/^CONFIG.*proxy.config.proxy_name STRING.*$/CONFIG proxy.config.proxy_name STRING FIXME.example.com/' \
	%{buildroot}/etc/trafficserver/records.config
perl -pi -e 's/^CONFIG.*proxy.config.ssl.server.cert.path.*$/CONFIG proxy.config.ssl.server.cert.path STRING \/etc\/pki\/tls\/certs\//' \
	%{buildroot}/etc/trafficserver/records.config
perl -pi -e 's/^CONFIG.*proxy.config.ssl.server.private_key.path.*$/CONFIG proxy.config.ssl.server.private_key.path STRING \/etc\/pki\/tls\/private\//' \
	%{buildroot}/etc/trafficserver/records.config

mkdir -p %{buildroot}%{_sysconfdir}
mv %{buildroot}%{_prefix}%{_sysconfdir} %{buildroot}%{_sysconfdir}/trafficserver
ln -s ../..%{_sysconfdir}/trafficserver %{buildroot}%{_prefix}%{_sysconfdir}

rm -rf %{buildroot}%{_prefix}%{_localstatedir}/*

mkdir -p %{buildroot}%{_localstatedir}/run/trafficserver
ln -s ../../..%{_localstatedir}/run/trafficserver %{buildroot}%{_prefix}%{_localstatedir}/run

mkdir -p %{buildroot}%{_localstatedir}/log/trafficserver
ln -s ../../..%{_localstatedir}/log/trafficserver %{buildroot}%{_prefix}%{_localstatedir}/logs

mkdir -p %{buildroot}%{_localstatedir}/cache/trafficserver
ln -s ../../..%{_localstatedir}/cache/trafficserver %{buildroot}%{_prefix}%{_localstatedir}/cache

%check
%ifnarch ppc64
make check %{?_smp_mflags} V=1
%endif

# The clean section  is only needed for EPEL and Fedora < 13
# http://fedoraproject.org/wiki/PackagingGuidelines#.25clean
%clean
rm -rf %{buildroot}


%post
/sbin/ldconfig
%if %{?fedora}0 > 170 || %{?rhel}0 > 60
  %systemd_post trafficserver.service
%else
  if [ $1 -eq 1 ] ; then
  %if %{?fedora}0 > 140
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
  %else
    /sbin/chkconfig --add %{name}
  %endif
  fi
%endif

%pre
getent group ats >/dev/null || groupadd -r ats -g 176 &>/dev/null
getent passwd ats >/dev/null || \
useradd -r -u 176 -g ats -d / -s /sbin/nologin \
	-c "Apache Traffic Server" ats &>/dev/null

%preun
%if %{?fedora}0 > 170 || %{?rhel}0 > 60
  %systemd_preun trafficserver.service
%else
if [ $1 -eq 0 ] ; then
  /sbin/service %{name} stop > /dev/null 2>&1
  /sbin/chkconfig --del %{name}
fi
%endif

%postun
/sbin/ldconfig

%if %{?fedora}0 > 170 || %{?rhel}0 > 60
  %systemd_postun_with_restart trafficserver.service
%else
if [ $1 -eq 1 ] ; then
  /sbin/service trafficserver condrestart &>/dev/null || :
fi
%endif

%files
%defattr(-, ats, ats, -)
%{!?_licensedir:%global license %%doc}
%license LICENSE
%doc README NOTICE
%attr(0755, ats, ats) %dir /etc/trafficserver
%config(noreplace) /etc/trafficserver/*
%config(noreplace) %{_sysconfdir}/sysconfig/trafficserver
%{_bindir}/traffic*
%{_bindir}/tspush
%dir %{_libdir}
%dir %{_libdir}/plugins
%{_libdir}/libts*.so.7*
%{_libdir}/libatscppapi*.so.7*
%{_libdir}/plugins/*.so
%if %{?fedora}0 > 140 || %{?rhel}0 > 60
/lib/systemd/system/trafficserver.service
%config(noreplace) %{_sysconfdir}/tmpfiles.d/trafficserver.conf
%else
/etc/init.d/trafficserver
%endif
%dir /var/log/trafficserver
%dir /var/run/trafficserver
%dir /var/cache/trafficserver
%{_prefix}%{_sysconfdir}
%{_prefix}%{_localstatedir}/run
%{_prefix}%{_localstatedir}/logs
%{_prefix}%{_localstatedir}/cache

%files perl
%defattr(-,root,root,-)
%{_prefix}/share/man/man3/*
%{_prefix}/lib/perl5/Apache/TS.pm.in
%{_prefix}/lib/perl5/Apache/TS.pm
%{_prefix}/lib/perl5/Apache/TS/*

%files devel
%defattr(-,root,root,-)
%{_bindir}/tsxs
%{_includedir}/ts
%{_includedir}/atscppapi
%{_libdir}/*.so
%{_libdir}/pkgconfig/trafficserver.pc

%changelog
* Thu Aug  3 2017 Hiroaki Nakamura <hnakamur@gmail.com> 7.1.0-1
- Update to 7.1.0 LTS release

* Wed Nov 16 2016 Hiroaki Nakamura <hnakamur@gmail.com> 7.0.0-2
- Remove expat-devel from build dependencies

* Wed Nov 16 2016 Hiroaki Nakamura <hnakamur@gmail.com> 7.0.0-1
- Update to 7.0.0 LTS release

* Fri Sep 30 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.2.0-2
- Return stale cache even if the origin server response has
  "Cache-Control: s-maxage" header.

* Wed Jul 27 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.2.0-1
- Update to 6.2.0 LTS release

* Fri May 20 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-10
- Add patch to add new value to proxy.config.http.cache.required_headers
  to require s-maxage for contents to be cached.
- Remove patch to concatenate multiple header values of
  the same name in TSLua.

* Wed May 11 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-9
- Fix bug in patch to concatenate multiple header values of
  the same name in TSLua.

* Tue May 10 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-8
- Concatenate multiple header values of the same name in TSLua.

* Wed Apr 27 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-7
- Remove patch to add proxy.config.http.cache.ignore_expires and
  proxy.config.http.cache.ignore_server_cc_max_age.

* Tue Apr 26 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-6
- Apply patch to add proxy.config.http.cache.ignore_expires and
  proxy.config.http.cache.ignore_server_cc_max_age.

* Wed Mar  9 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-5
- Disable patch to enable unix domain socket.

* Mon Mar  7 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-4
- Apply patch to enable unix domain socket.

* Sun Feb 14 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-3
- Enable luajit

* Sun Feb 14 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-2
- Set prefix to /opt/trafficserver and use relative directories

* Tue Feb  9 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.1-1
- Update to 6.1.1 LTS release

* Wed Feb  3 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.1.0-1
- Update to 6.1.0 LTS release

* Wed Jan 13 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.0.0-3
- Build experimental plugins

* Fri Jan  1 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.0.0-2
- Just use configure --disable-luajit without a patch or deleting files

* Fri Jan  1 2016 Hiroaki Nakamura <hnakamur@gmail.com> 6.0.0-1
- Update to 6.0.0 LTS release

* Fri Jan  1 2016 Hiroaki Nakamura <hnakamur@gmail.com> 5.3.0-2
- Add patch to cache_insepector to split multiline URLs correctly

* Sun Jun 21 2015 Peter Robinson <pbrobinson@fedoraproject.org> 5.3.0-1
- Update to 5.3.0 LTS release
- Build on aarch64 and power64
- Split perl bindings to sub package
- Cleanup and modernise spec

* Fri Jun 19 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 5.0.1-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sat May 02 2015 Kalev Lember <kalevlember@gmail.com> - 5.0.1-3
- Rebuilt for GCC 5 C++11 ABI change

* Mon Jan 26 2015 Petr Machata <pmachata@redhat.com> - 5.0.1-2
- Rebuild for boost 1.57.0

* Mon Aug 18 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 5.0.1-1
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Wed Jul 23 2014 Jan-Frode Myklebust <janfrode@tanso.net> - 5.0.1-0
- Fix CVE-2014-3525

* Wed Jul 16 2014 Jan-Frode Myklebust <janfrode@tanso.net> - 5.0.0-0
- New major version.

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.2.1-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Thu May 22 2014 Petr Machata <pmachata@redhat.com> - 4.2.1-4
- Rebuild for boost 1.55.0

* Wed May 21 2014 Jaroslav Škarvada <jskarvad@redhat.com> - 4.2.1-3
- Rebuilt for https://fedoraproject.org/wiki/Changes/f21tcl86

* Wed Apr 30 2014 Jan-Frode Myklebust <janfrode@tanso.net> - 4.2.1-2
- Bump release tag. RC1 became final.

* Sat Apr 26 2014 Jan-Frode Myklebust <janfrode@tanso.net> - 4.2.1-rc1
- Update to 4.2.1-RC1

* Thu Apr 10 2014 Jan-Frode Myklebust <janfrode@tanso.net> - 4.2.0-0
- Update to 4.2.0

* Tue Dec 17 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 4.1.2-0
- Bump to final. No change from rc0.
- What's new: https://cwiki.apache.org/confluence/display/TS/What%27s+new+in+v4.1.x

* Thu Dec 12 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 4.1.2-rc0
- Update to 4.1.2-rc0.

* Mon Nov 11 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 4.0.2-5
- Buildrequire hwloc-devel, since it supposedly gives tremendous 
  positive performance impact to use hwlock to optimize scaling and
  number of threads and alignment for actual hardware we're running on.

* Sun Oct 20 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 4.0.2-3
- Rebuild for picking up ECC/ECDHE/EC/ECDSA/elliptic curves
  which are now enabled in OpenSSL.

* Fri Oct 11 2013 Ralf Corsépius <corsepiu@fedoraproject.org> - 4.0.2-3
- Add BR: systemd for systemd.macros (RHBZ #1018080).

* Thu Oct 10 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 4.0.2-2
- Update to 4.0.2, which fixes the following bugs:

    [TS-2144] - traffic_server crashes when clearing cache
    [TS-2173] - cache total hit/miss stats broken in version 4.0.1
    [TS-2174] - traffic_shell/traffic_line miss some stats value
    [TS-2191] - when http_info enabled, the http_sm may be deleted but a event associated it not cancelled.
    [TS-2207] - Centos5 out of tree perl build fails
    [TS-2217] - remove the option to turn off body factory - setting it to 0 will result in empty responses

- Automatically verify GPG signature during RPM prep.
- Build requires boost-devel.

* Tue Sep 3 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 4.0.1-1
- Update to 4.0.1.  What's new in v4.0.0:
  https://cwiki.apache.org/confluence/display/TS/What%27s+new+in+v4.0.0

- Upgrade instructions from earlier versions:
  https://cwiki.apache.org/confluence/display/TS/Upgrading+to+v4.0

  Important notes:

    proxy.config.remap.use_remap_processor has been removed,
    use the proxy.config.remap.num_remap_threads instead.

    Default proxy.config.cache.ram_cache.size has been increased by 
    a magnitude.

    Support for pre v3.2 port configuration directives has been removed.

    The following records.config parameters should be removed:

	CONFIG proxy.config.bandwidth_mgmt.filename STRING ""
	CONFIG proxy.config.admin.autoconf.wpad_filename STRING ""
	CONFIG proxy.config.username.cache.enabled INT 0
	CONFIG proxy.config.username.cache.filename STRING ""
	CONFIG proxy.config.username.cache.size INT 0
	CONFIG proxy.config.username.cache.storage_path STRING ""
	CONFIG proxy.config.username.cache.storage_size INT 0
	CONFIG proxy.config.http.wuts_enabled INT 0
	CONFIG proxy.config.http.log_spider_codes INT 0
	CONFIG proxy.config.http.accept_encoding_filter_enabled INT 0
	CONFIG proxy.config.http.accept_encoding_filter.filename STRING ""
	CONFIG proxy.config.net.throttle_enabled INT 0
	CONFIG proxy.config.net.accept_throttle INT 0
	CONFIG proxy.config.cluster.num_of_cluster_connections INT 0
	CONFIG proxy.config.cache.url_hash_method INT 0
	CONFIG proxy.config.plugin.extensions_dir STRING ""
	CONFIG proxy.local.http.parent_proxy.disable_connect_tunneling INT 0
	CONFIG proxy.config.remap.use_remap_processor INT 0

* Sun Aug 25 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.5-3
- bz#994224 Use rpm configure macro, instead of calling configure
  directly.

* Fri Aug 9 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.5-2
- bz#994224 Pass RPM_OPT_FLAGS as environment variables to configure,
  instead of overriding on make commandline. Thanks Dimitry Andric!

* Thu Aug 1 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.5-1
- Update to v3.2.5 which fixes the following bugs:

  [TS-1923] Fix memory issue caused by resolve_logfield_string()
  [TS-1918] SSL hangs after origin handshake.
  [TS-1483] Manager uses hardcoded FD limit causing restarts forever on traffic_server.
  [TS-1784] Fix FreeBSD block calculation (both RAW and directory)
  [TS-1905] TS hangs (dead lock) on HTTPS POST/PROPFIND requests.
  [TS-1785, TS-1904] Fixes to make it build with gcc-4.8.x.
  [TS-1903] Remove JEMALLOC_P use, it seems to have been deprecated.
  [TS-1902] Remove iconv as dependency.
  [TS-1900] Detect and link libhwloc on Ubuntu.
  [TS-1470] Fix cache sizes > 16TB (part 2 - Don't reset the cache after restart)

* Mon Jun 3 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.4-3
- Harden build with PIE flags, ref bz#955127. 

* Sat Jan 19 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.4-1
- Update to 3.2.4 release candiate

* Fri Jan 4 2013 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.3-1
- Update to v3.2.3. Remove patches no longer needed.

* Fri Aug 24 2012 Václav Pavlín <vpavlin@redhat.com> - 3.2.0-6
- Scriptlets replaced with new systemd macros (#851462)

* Thu Aug 16 2012 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.0-5
- Add patch for TS-1392, to fix problem with SNI fallback.

* Sun Jul 22 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 3.2.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Mon Jun 25 2012 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.0-2
- Remove duplicate man-pages.

* Sat Jun 23 2012 Jan-Frode Myklebust <janfrode@tanso.net> - 3.2.0-1
- Update to v3.2.0

* Sun Jun 10 2012 Jan-Frode Myklebust <janfrode@tanso.net> - 3.0.5-1
- Remove trafficserver-gcc47.patch since it's fixed upstream, TS-1116.
- Join trafficserver-condrestart.patch into trafficserver-init_scripts.patch,
  and clean out not needed junk.

* Fri Apr 13 2012 Jan-Frode Myklebust <janfrode@tanso.net> - 3.0.4-5
- Add hardened build.

* Wed Apr 11 2012 <janfrode@tanso.net> - 3.0.4-4
- Add patch for gcc-4.7 build issues.

* Mon Apr 9 2012 Dan Horák <dan[at]danny.cz> - 3.0.4-3
- switch to ExclusiveArch

* Fri Mar 23 2012 <janfrode@tanso.net> - 3.0.4-2
- Create /var/run/trafficserver using tmpfiles.d on f15+.

* Thu Mar 22 2012 <janfrode@tanso.net> - 3.0.4-1
- Update to new upstream release, v3.0.4.
- remove trafficserver-cluster_interface_linux.patch since this was fixed upstream, TS-845.

* Thu Mar 22 2012 <janfrode@tanso.net> - 3.0.3-6
- Remove pidfile from systemd service file. This is a type=simple
  service, so pidfile shouldn't be needed.

* Wed Mar 21 2012 <janfrode@tanso.net> - 3.0.3-5
- Add systemd support.
- Drop init.d-script on systemd-systems.

* Sun Mar 18 2012 <janfrode@tanso.net> - 3.0.3-3
- change default proxy.config.proxy_name to FIXME.example.com instead of the
  name of the buildhost
- configure proxy.config.ssl.server.cert.path and
  proxy.config.ssl.server.private_key.path to point to the standard /etc/pki/
  locations.

* Tue Mar 13 2012 <janfrode@tanso.net> - 3.0.3-2
- exclude ppc/ppc64 since build there fails, TS-1131.

* Sat Mar 10 2012 <janfrode@tanso.net> - 3.0.3-1
- Removed mixed use of spaces and tabs in specfile.

* Mon Feb 13 2012 <janfrode@tanso.net> - 3.0.3-0
- Update to v3.0.3

* Thu Dec 8 2011 <janfrode@tanso.net> - 3.0.2-0
- Update to v3.0.2
- Fix conderestart in initscript, TS-885.

* Tue Jul 19 2011 <janfrode@tanso.net> - 3.0.1-0
- Update to v3.0.1
- Remove uninstall-hook from trafficserver_make_install.patch, removed in v3.0.1.

* Thu Jun 30 2011 <janfrode@tanso.net> - 3.0.0-6
- Note FIXME's on top.
- Remove .la and static libs.
- mktemp'd buildroot.
- include license

* Mon Jun 27 2011 <janfrode@tanso.net> - 3.0.0-5
- Rename patches to start with trafficserver-.
- Remove odd version macro.
- Clean up mixed-use-of-spaces-and-tabs.

* Wed Jun 22 2011 <janfrode@tanso.net> - 3.0.0-4
- Use dedicated user/group ats/ats.
- Restart on upgrades.

* Thu Jun 16 2011 <zym@apache.org> - 3.0.0-3
- update man pages, sugest from Jan-Frode Myklebust <janfrode@tanso.net>
- patch records.config to fix the crashing with cluster iface is noexist
- cleanup spec file

* Wed Jun 15 2011 <zym@apache.org> - 3.0.0-2
- bump to version 3.0.0 stable release
- cleanup the spec file and patches

* Tue May 24 2011 <yonghao@taobao.com> - 2.1.8-2
- fix tcl linking

* Thu May  5 2011 <yonghao@taobao.com> - 2.1.8-1
- bump to 2.1.8
- comment out wccp

* Fri Apr  1 2011 <yonghao@taobao.com> - 2.1.7-3
- enable wccp and fixed compile warning
- never depends on sqlite and db4, add libz and xz-libs
- fix libary permission, do post ldconfig updates

* Sun Mar 27 2011 <yonghao@taobao.com> - 2.1.7-2
- patch traffic_shell fix

* Tue Mar 22 2011 <yonghao@taobao.com> - 2.1.7-1
- bump to v2.1.7
- fix centos5 building
- drop duplicated patches

* Sat Mar 12 2011 <yonghao@taobao.com> - 2.1.6-2
- fix gcc 4.6 building
- split into -devel package for devel libs
- fix init scripts for rpmlint requirement
- fix install scripts to build in mock, without root privileges

* Tue Mar 01 2011 <yonghao@taobao.com> - 2.1.6-1
- bump to 2.1.6 unstable
- replace config layout name as Fedora

* Thu Nov 18 2010 <yonghao@taobao.com> - 2.1.4
- initial release for public
- original spec file is from neomanontheway@gmail.com
