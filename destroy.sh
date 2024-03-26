#!/bin/bash

terraform -chdir=./IaC/ destroy -auto-approve

rm -rf ./IaC/stablespot-create-spot.zip
rm -rf ./IaC/stablespot-migration-by-interrupt.zip
rm -rf ./IaC/stablespot-paginator.zip
rm -rf ./IaC/stablespot-controller.zip
rm -rf ./IaC/stablespot-registor.zip
rm -rf ./stablespotenv
rm -rf ./python
rm -rf ./IaC/jose_layer.zip
