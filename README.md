Record Priorizer Service for TVHeadend

A service for priorizing recordings on STD (Single Transponder Decryption) environments. This service priorizes recording 
tasks over normal access (like viewing TV only) on devices, Common Interfaces or other configurations, where only single 
transponder decryption is available. That means this service guarantee recordings when only one encrypted transponder/channel 
is available at same time by wiping out other clients.

This service is only available on client server configurations with TVHeadend as a server available. When running in a multi
client cluster, all clients must have access to the timers of other devices in this cluster (see TVHeadend configuration, 
users, access, video recorder).