#!/bin/bash

rm -rf ./IaC/stablespot-create-spot.zip
rm -rf ./IaC/stablespot-migration-by-interrupt.zip
rm -rf ./IaC/stablespot-paginator.zip
rm -rf ./IaC/stablespot-controller.zip
rm -rf ./IaC/stablespot-registor.zip

terraform -chdir=./IaC/ destroy -auto-approve
