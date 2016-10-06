==================
 MLNX agent enable
==================

1) Download DevStack

2) Add this as an external repository::

    enable_plugin neutron_ml2_mlnx git://github.com/openstack/networking-mlnx <branch>

3) update Q_ML2_PLUGIN_MECHANISM_DRIVERS with mlnx_infiniband mech driver::

    Q_ML2_PLUGIN_MECHANISM_DRIVERS=mlnx_infiniband,openvswitch

4) enable switchd mlnx-agt and mlnx_dnsmasq services::

    enable_service mlnx-agt eswitchd mlnx_dnsmasq

5) run ``stack.sh``


==========================================
 SDN Mechanism Driver Enabling in Devstack
==========================================

1) Download DevStack

2) Add this external repository:
    enable_plugin neutron_ml2_mlnx git://github.com/openstack/networking-mlnx <branch>

3) Add SDN plugin to mechanism drivers plugins list:
    Q_ML2_PLUGIN_MECHANISM_DRIVERS=mlnx_sdn_assist,openvswitch

4) Add SDN mandatory configurations, for example::

    [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
    [sdn]
    url = http://<sdn_provider_ip>/neo
    domain = cloudx
    username = admin
    password = admin

5) run ``stack.sh``
