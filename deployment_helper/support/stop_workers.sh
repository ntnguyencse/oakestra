hostname=""

hostname_to_ip()
{
  	while IFS=, read localhostname localip; do
        	if [[ $hostname == $localhostname ]]; then
			ip=$localip
			break
		fi
	done < node.txt
}

echo "\n"
echo "#####################"
echo "### Nodes Restart ###"
echo "#####################"

clusterlist=""
for cluster in $(cat cluster.txt); do
        clusterlist=$clusterlist""$cluster" "
done

###### Instantiate nodes ######
workernum=1
for cluster in $clusterlist; do
	echo "## Restarting workers for cluster $cluster ##"
	hostlist=""
	for host in $(cat $cluster.txt); do	
		hostlist=$hostlist""$host" "
	done
	hostname=$cluster
	hostname_to_ip
	clusterip=$ip
	echo "Clusterip: $ip"
	
	for host in $hostlist; do
		hostname=$host
		hostname_to_ip
		
		echo "Stopping: <$hostname,$ip> [If any error shows up... don't worry :D"
                ssh -oStrictHostKeyChecking=no $1@$ip "num=\$(ps aux | grep start-up | grep -v grep | awk '{print \$2}'); sudo kill \$num"
                ssh -oStrictHostKeyChecking=no $1@$ip "num=\$(ps aux | grep NetManager | grep -v grep | awk '{print \$2}'); sudo kill -9 \$num"
                ssh -oStrictHostKeyChecking=no $1@$ip "num=\$(ps aux | grep node_engine | grep -v grep | awk '{print \$2}'); sudo kill -9 \$num"
		ssh -oStrictHostKeyChecking=no $1@$ip "docker container prune -f"
		echo "Done!"
		
		woerkernum=$((workernum+1))
	done
done

echo "############################################"
echo "#All nodes have been restarted succesfully.#"
echo "############################################"