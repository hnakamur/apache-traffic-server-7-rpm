#!/bin/bash
sudo timedatectl set-timezone Asia/Tokyo

sudo yum -y install mock rpm-build rpmdevtools patch sudo curl less scl-utils scl-utils-build
sudo usermod -a -G mock $USER

rpmdev-setuptree
echo '%_sourcedir %{_topdir}/SOURCES/%{name}' >> ~/.rpmmacros

rsync -a ~/sync/SPECS/ ~/rpmbuild/SPECS/
mkdir -p ~/rpmbuild/SOURCES/trafficserver
rsync -a ~/sync/SOURCES/ ~/rpmbuild/SOURCES/trafficserver/
rsync -a ~/sync/scripts/ ~/sync/.envrc ~/rpmbuild/
chmod +x ~/rpmbuild/*.sh
