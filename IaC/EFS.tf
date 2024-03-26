resource "aws_security_group" "efs-sg" {
  vpc_id = aws_vpc.stablespot_vpc.id
  name   = "${var.prefix}-efs-sg"
  egress = [{
    cidr_blocks      = ["0.0.0.0/0"]
    from_port        = 0
    protocol         = -1
    to_port          = 0
    description      = "sg"
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }]
  ingress = [{
    cidr_blocks      = ["0.0.0.0/0"]
    from_port        = 2049
    protocol         = "tcp"
    to_port          = 2049
    description      = "sg"
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }]
}

resource "aws_efs_file_system" "efs" {
  creation_token = "${var.prefix}-efs"
}

resource "aws_efs_mount_target" "efs-mount-target" {
  count = length(data.aws_availability_zones.available.names)
  subnet_id       = aws_subnet.stablespot_public_subnet[count.index].id
  file_system_id  = aws_efs_file_system.efs.id
  security_groups = [aws_security_group.efs-sg.id]
}

resource "aws_efs_access_point" "efs-access-point" {
  file_system_id = aws_efs_file_system.efs.id
  
  posix_user {
    gid = 1000
    uid = 1000
  }
  
  root_directory {
    path = "/efs"
    creation_info {
      owner_gid = 1000
      owner_uid = 1000
      permissions = "777"
    }
  }
}
