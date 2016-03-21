# plugin.sh - DevStack extras script to install mlnx_infiniband MD

source ${DEST}/neutron_ml2_mlnx/devstack/lib/neutron_ml2_mlnx

if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
    # Set up system services
    # no-op
    :

elif [[ "$1" == "stack" && "$2" == "install" ]]; then
    # Perform installation of service source
    echo_summary "Installing MLNX Ml2 MD"
    install_neutron_ml2_mlnx

elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    # Configure after the other layer 1 and 2 services have been configured
    echo_summary "Configuring MLNX Ml2 MD"
    configure_neutron_ml2_mlnx

elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    # Initialize and start the template service
    ##init_template
    start_neutron_ml2_mlnx
fi

if [[ "$1" == "unstack" ]]; then
    # Shut down template services
    stop_neutron_ml2_mlnx
fi

if [[ "$1" == "clean" ]]; then
    # Remove state and transient data
    # Remember clean.sh first calls unstack.sh
    # no-op
    cleanup_neutron_ml2_mlnx
fi
