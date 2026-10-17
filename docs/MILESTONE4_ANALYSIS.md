# Milestone 4 - What survives if our VM is deleted?

If our VM were deleted, our website at `35.202.153.219:8000` would stop working.
Active requests, open browser connections, in-memory rate-limit counters, and
temporary refresh files would be lost. Our background schedule and alert refresh
tasks would also stop until we restored compute. We have one VM and no automatic
failover, so decoupling state removes data loss from a VM failure but does not
remove downtime.

Our transit database would survive in Cloud SQL for PostgreSQL. The instance is
separate from the VM, has private address `10.164.0.3`, and has no public IP.
It connects through Private Services Access on `metroai-vpc`; our VM uses
`metroai-subnet` (`10.42.0.0/24`). The database stores our transit tables, GIS
reference data, saved alert cache, and upload metadata. Our committed migration
contains real `CREATE TABLE` statements. We copied a consistent snapshot of our
old database and compared all 13 source tables. In particular, the old and new
counts match for 8,803 stops, 120 routes, 21,878 trips, and 1,414,850 stop-time
records. Original migration snapshots are also retained in our private bucket.
Daily database backups retain seven copies; they do not make this zonal instance
highly available.

Uploaded files would survive in our Cloud Storage bucket,
`metroai-vm-milestone-20260922-uploads`. The application streams uploads to
Cloud Storage and stores their names, object generations, sizes, and hashes in
PostgreSQL. Files are not kept in a Docker volume. Public bucket access is
prevented; the app accesses objects through the attached `metroai-runtime`
service account using short-lived metadata credentials. We created no downloaded
service-account key. The coursework app has no user-account system, so its VM
firewall restricts access to the presenter's IP.

Our API keys and database credentials would survive in Secret Manager. The app
fetches its four runtime secrets into process memory through the VM identity;
the administrator password is a separate secret that this identity cannot read.
The running container has no `.env` file, no secret-bearing environment
variables, and no persistent data mounts. Its root filesystem is read-only;
`/tmp` is disposable. Our image-layer scan checks the current credentials for
accidental inclusion, but it is not proof about unknown credentials.

Our published image, GitHub source, service account, IAM grants, bucket, private
network, and reserved public IP remain independent resources. To recover, we
must create a VM in the same subnet, attach the same identity and firewall tag,
assign the reserved IP, and run our saved startup script. We verified state
persistence by recreating the application container; we did not delete the VM.
Cloud SQL, storage, secrets, and the reserved IP can continue to incur costs
during downtime. We retain our $50 monthly budget and spending alerts; these
notify us and do not stop resources automatically.
