resource "aws_vpc" "stablespot_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.prefix}-vpc"
  }
}

resource "aws_internet_gateway" "stablespot_igw" {
  vpc_id = aws_vpc.stablespot_vpc.id

  tags = {
    Name = "${var.prefix}-igw"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name = "region-name"
    values = [ "${var.region}" ]
  }
  filter {
    name = "zone-type"
    values = [ "availability-zone" ]
  }
}

resource "aws_subnet" "stablespot_public_subnet" {
  count                   = length(data.aws_availability_zones.available.names)
  vpc_id                  = aws_vpc.stablespot_vpc.id
  cidr_block              = cidrsubnet(aws_vpc.stablespot_vpc.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.prefix}-public-${count.index}"
  }
}

resource "aws_subnet" "stablespot_private_subnet" {
  count             = length(data.aws_availability_zones.available.names)
  vpc_id            = aws_vpc.stablespot_vpc.id
  cidr_block        = cidrsubnet(aws_vpc.stablespot_vpc.cidr_block, 8, count.index + length(data.aws_availability_zones.available.names))
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.prefix}-private-${count.index}"
  }
}

resource "aws_route_table" "stablespot_public_route_table" {
  vpc_id = aws_vpc.stablespot_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.stablespot_igw.id
  }

  tags = {
    Name = "${var.prefix}-public-route-table"
  }
}

resource "aws_route_table_association" "stablespot_public_route_table_association" {
  count          = length(aws_subnet.stablespot_public_subnet)
  subnet_id      = aws_subnet.stablespot_public_subnet[count.index].id
  route_table_id = aws_route_table.stablespot_public_route_table.id
}
