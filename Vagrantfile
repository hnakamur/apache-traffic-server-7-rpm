# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "centos/7"
  config.vm.network "private_network", ip: "192.168.33.132"
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "1024"
  end
  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.provision "shell", privileged: false, path: "setup.sh"
end
