#!/bin/bash

usage() {
	echo "Usage:";
	echo "- $0 deploy [path to private ssh key] [IP] [env vars to write to .env] : lance une mise en production";
	echo "- $0 test [path to private ssh key] [URL to test] : lance une sequence de tests";
	echo "- $0 restore [docker archive] : lance une restauration de docker";
}

livraison() {
	local IP="$1";
	local ARG="$2";
	local ENV="$3";

	[ "$ARG" != "" ] && RSA="-i $ARG" || RSA="";
	read -r -d "" SCRIPT <<EOF
	  if [  ]
	  then

	  fi
		cd /home/docker/jepostule;
		git reset --hard HEAD;
		git checkout $CI_COMMIT_BRANCH &&
		git pull &&
		[ "$ENV" != "" ] && echo "$ENV" >.env; \
		docker-compose up -d --build 1>/dev/null && \
		docker-compose restart jepostule;
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
		livraison "$IP" "$ARG" "$ENV";
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

