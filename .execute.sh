#!/bin/bash

usage() {
  cat <<EOF
Usages:

  $0 ACTION [ ARGS ... ]

ACTIONS
  connect_vpn   Connecte le serveur au vpn
  deploy        Lance une mise en production
  restore       List les backups disponible ou lance une restauration de docker

ARGS

connect_vpn VPN_CONFIG [TIMEOUT]

  VPN_CONFIG     openvpn config
  TIMEOUT        timeout in seconds (default: 30)


deploy IP [ IDENTITY_FILE [ ENV [ COMMIT_REF ] ] ]

  IP             server IP address
  IDENTITY_FILE  path to private ssh key. Use ssh default ssk key if empty (default: "")
  ENV            env vars to write to .env. Don't change the .env if empty (default: "")
  COMMIT_REF     commit ref to be deploy (default: $CI_COMMIT_SHA or $GITHUB_SHA)


restore [ ARCHIVE_NAME ]

  ARCHIVE_NAME   docker archive to restore. List the available archive if empty (default: "")
EOF
}

log_on_error() {
  local RESULT="$1"
  local ERROR_MESSAGE="$2"

  if [ "$RESULT" -gt 0 ]
  then
    echo "$ERROR_MESSAGE" 1>&2
  fi
  return "$RESULT"
}

connect_openvpn() {
  local VPN_CONFIG="$1";
  local TIMEOUT="${2:-30}"

  local openvpn=$(mktemp --tmpdir="$RUNNER_TEMP" --suffix=.ovpn);
  local watch_file=$(mktemp --tmpdir="$RUNNER_TEMP" --dry-run);
  local bash_path=$(command -v bash);

  echo "$VPN_CONFIG" > ${openvpn};

  sudo openvpn \
    --dev tun0 \
    --config ${openvpn} \
    --script-security 2 \
    --daemon \
    --up "'$bash_path' -c 'touch $watch_file'";

  timeout "${TIMEOUT}" bash -c "until [ -e \"$watch_file\" ]; do sleep 1; done"
  log_on_error "$?" "VPN not up after ${TIMEOUT} seconds"
}

livraison() {
	local IP="$1";
	local IDENTITY_FILE="${2:-}";
	local ENV="${3:-}";
	local COMMIT_REF="${5:-${CI_COMMIT_SHA:-${GITHUB_SHA}}}"

	[ "$IDENTITY_FILE" != "" ] && RSA="-i $IDENTITY_FILE" || RSA="";
	read -r -d "" SCRIPT <<EOF
	  set -e
	  if [[ ! -e /home/docker/importer ]]
	  then
      git clone https://github.com/StartupsPoleEmploi/lbb-importer.git /home/docker/importer
	  fi
		cd /home/docker/importer;
		git fetch --all --prune
		git checkout $COMMIT_REF;
		[ "$ENV" != "" ] && echo "$ENV" >.env || true;
		docker-compose up -d --build --remove-orphans 1>/dev/null;
		docker-compose restart;
EOF
	[ "$ENV" != "" ] && SCRIPT=`echo "export ENV='$ENV'; $SCRIPT"`;
	ssh -Ctt livraison@$IP $RSA -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$SCRIPT";
}

if [ -f .env ]; then source .env; fi

CMD=$1;

case $CMD in
	deploy)
		IP="$2";
    IDENTITY_FILE="${3:-}";
		ENV="${4:-}";
		COMMIT_REF="${5:-}"

		livraison "$IP" "$IDENTITY_FILE" "$ENV";
		;;
  connect_openvpn)
    VPN_CONFIG="$2";

    connect_openvpn "$VPN_CONFIG"
    ;;
	restore)
	  ARCHIVE_NAME="${2:-}"

		if [ "$ARCHIVE_NAME" = "" ];
		then
			echo "### Liste des archives";
			ls -1 backups/home/backups | grep -E ".*\.bz2";
			echo;
			echo "Essayer:";
			echo "$0 restore <fichier>";
		else
			tar -jxvf backups/home/backups/$ARCHIVE_NAME;
		fi
		;;
	*)
		usage;
		;;
esac

