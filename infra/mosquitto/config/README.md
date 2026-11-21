# Mosquitto Config Setup
1. Copy ACL template: cp infra/mosquitto/acl.template infra/mosquitto/config/acl
2. Create password file for API user:
   docker compose -f infra/docker-compose.yml run --rm mqtt mosquitto_passwd -c /mosquitto/config/password_file farmlink-api
(Device users are added later by API provisioning; do not commit acl or password_file).
