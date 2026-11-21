# Local Dev Certificates
1. Generate CA: openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ca.key -out ca.crt -subj "/CN=DevCA"
2. Generate server key & CSR: openssl req -nodes -newkey rsa:2048 -keyout server.key -out server.csr -subj "/CN=localhost"
3. Sign server cert: openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365
Outputs ca.crt, server.crt, and server.key required by Mosquitto TLS listener.
