==================
 MLNX agent enable
==================

1) Starting from Kilo add the following line:
    enable_plugin neutron_ml2_mlnx  git://git.openstack.org/stackforge/networking-mlnx

2) In a versions older than Kilo add:
    Q_ML2_PLUGIN_MECHANISM_DRIVERS=mlnx,openvswitch
    enable_service mlnx-agt eswitchd

==========================================
 SDN Mechanism Driver Enabling in Devstack
==========================================

1) Download DevStack

2) Add this external repository:
    enable_plugin neutron_ml2_mlnx  git://git.openstack.org/stackforge/networking-mlnx

3) Add SDN plugin to mechanism drivers plugins list:
    Q_ML2_PLUGIN_MECHANISM_DRIVERS=sdnmechdriver,openvswitch

4) Add SDN mandatory configurations, for example:
    [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
    [sdn]
    url = http://<sdn_provider_ip>/openstack_api
    domain = cloudx
    username = admin
    password = admin

5) run ``stack.sh``
