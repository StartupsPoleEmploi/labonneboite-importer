#!/bin/bash

usage() {
	echo "Usage:";
	echo "- $0 deploy [path to private ssh key] [IP] [env vars to write to .env] : lance une mise en production";
	echo "- $0 test [path to private ssh key] [URL to test] : lance une sequence de tests";
	echo "- $0 restore [docker archive] : lance une restauration de docker";
}

connect_openvpn() {
  local VPN_CONFIG="$1";

  ovpn=$(mktemp --suffix=.ovpn)
  echo "$VPN_CONFIG" > ${ovpn}
  sudo openvpn --dev tun0 --daemon --config ${ovpn}
}

livraison() {
	local IP="$1";
	local ARG="$2";
	local ENV="$3";
  local VPN_CONFIG="$4";

  echo ${IP:0:3}
  echo ${#VPN_CONFIG}
  echo ${#ENV}

  [ "$VPN_CONFIG" != "" ] && (connect_openvpn "${VPN_CONFIG}" || return $?);
	[ "$ARG" != "" ] && RSA="-i $ARG" || RSA="";
	read -r -d "" SCRIPT <<EOF
	  if [[ ! -e /home/docker/importer ]]
	  then
      git clone git@github.com:StartupsPoleEmploi/lbb-importer.git /home/docker/importer
	  fi
		cd /home/docker/importer;
		git reset --hard HEAD;
		git checkout $CI_COMMIT_BRANCH &&
		git pull &&
		[ "$ENV" != "" ] && echo "$ENV" >.env; \
		docker-compose up -d --build 1>/dev/null && \
		docker-compose restart;
EOF
	[ "$ENV" != "" ] && SCRIPT=`echo "export ENV='$ENV'; $SCRIPT"`;
	ssh -Ctt livraison@$IP $RSA -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SCRIPT";
}

if [ -f .env ]; then source .env; fi

CMD=$1;
ARG="$2";

case $CMD in
	deploy)
		IP="$3";
		ENV="$4";
		VPN_CONFIG="$5";
		livraison "$IP" "$ARG" "$ENV" "$VPN_CONFIG";
		;;
	test)
		DOMAIN="$3";
		curl -s https://$DOMAIN | grep -i "logo" >/dev/null && echo "Test Ok" || echo "Test Ko";
		;;
	restore)
		if [ "$ARG" = "" ];
		then
			echo "### Liste des archives";
			ls -1 backups/home/backups | grep -E ".*\.bz2";
			echo;
			echo "Essayer:";
			echo "$0 restore <fichier>";
		else
			tar -jxvf backups/home/backups/$ARG;
		fi
		;;
	*)
		usage;
		;;
esac

