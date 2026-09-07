# Oracle Always Free deployment

FleetOpt uses two `VM.Standard.E2.1.Micro` instances because the API and optimizer
have incompatible scikit-learn requirements and do not fit safely together in
one 1 GB VM.

- `fleetopt-api`: FastAPI on `127.0.0.1:8000`, published through Caddy HTTPS.
- `fleetopt-worker`: optimizer worker with an ephemeral public IP used only for
  outbound dependency and MongoDB Atlas access. It does not publish an HTTP
  service or application port.

Run `bootstrap-host.sh api` on the API VM and `bootstrap-host.sh worker` on the
worker VM. Install `requirements.txt` into `/opt/fleetopt/api-venv` and
`optimizer-requirements.txt` into `/opt/fleetopt/worker-venv`. Keep production
environment files at `/etc/fleetopt/api.env` and `/etc/fleetopt/worker.env` with
mode `0640`; never commit them.

The API security list should expose only ports 80 and 443 publicly. Restrict
port 22 to the deployment workstation and the API private IP used to reach the
worker. Port 8000 must remain private. The worker host firewall must reject new
inbound traffic except restricted SSH, even while its ephemeral public IP is
present. A private subnet with a NAT gateway is the preferred long-term worker
layout when that infrastructure is available within the deployment budget.

MongoDB Atlas access should use the API and worker public IPs as separate `/32`
entries. Do not leave `0.0.0.0/0` enabled after both hosts have stable egress
addresses.

## Updating the deployed backend

Run these commands from Git Bash at the repository root after the backend
change has been tested and committed. `git archive` sends only committed files,
so local `.env` files, QA output, and other ignored files are not uploaded.

```bash
API_HOST=137.23.38.111
WORKER_HOST=10.0.0.22
SSH_KEY="$HOME/.ssh/fleetopt_oracle_ed25519"

# Update the API host.
git archive --format=tar HEAD backend | \
  ssh -i "$SSH_KEY" ubuntu@"$API_HOST" \
  'sudo -u fleetopt tar -xf - -C /opt/fleetopt'

ssh -i "$SSH_KEY" ubuntu@"$API_HOST" \
  'sudo /opt/fleetopt/api-venv/bin/pip install -r /opt/fleetopt/backend/requirements.txt &&
   sudo systemctl restart fleetopt-api.service &&
   sudo systemctl is-active fleetopt-api.service'

# Update the worker through the API jump host.
PROXY_COMMAND="ssh -i \"$SSH_KEY\" -W %h:%p ubuntu@$API_HOST"
git archive --format=tar HEAD backend | \
  ssh -o "ProxyCommand=$PROXY_COMMAND" -i "$SSH_KEY" \
  ubuntu@"$WORKER_HOST" \
  'sudo -u fleetopt tar -xf - -C /opt/fleetopt'

ssh -o "ProxyCommand=$PROXY_COMMAND" -i "$SSH_KEY" \
  ubuntu@"$WORKER_HOST" \
  'sudo /opt/fleetopt/worker-venv/bin/pip install -r /opt/fleetopt/backend/optimizer-requirements.txt &&
   sudo systemctl restart fleetopt-worker.service &&
   sudo systemctl is-active fleetopt-worker.service'
```

Verify HTTPS, MongoDB, and recent service logs after every update:

```bash
curl -fsS https://137-23-38-111.sslip.io/api/health
curl -fsS https://137-23-38-111.sslip.io/api/health/db

ssh -i "$SSH_KEY" ubuntu@"$API_HOST" \
  'sudo journalctl -u fleetopt-api.service -n 100 --no-pager'

ssh -o "ProxyCommand=$PROXY_COMMAND" -i "$SSH_KEY" \
  ubuntu@"$WORKER_HOST" \
  'sudo journalctl -u fleetopt-worker.service -n 100 --no-pager'
```

If an update fails, check out the last known-good commit locally and repeat the
same `git archive` commands, then restart both services. Production secrets stay
in `/etc/fleetopt/api.env` and `/etc/fleetopt/worker.env`; update those files
through SSH only when an environment value changes. If Oracle replaces the
ephemeral API public IP, update the `API_HOST`, sslip.io hostname, Caddy
environment, frontend API URL, and Atlas `/32` network entry together.
