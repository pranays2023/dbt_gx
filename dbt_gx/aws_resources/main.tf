#Below block will configure backend to store terraform state
variable "AWS_ACCESS_KEY_ID" {
  default = ""
}
variable "AWS_SECRET_ACCESS_KEY" {
  default = ""
}

terraform {
  backend "s3" {
    bucket = "data-engg-onboarding" #This will be the bucket where tfstate will be stored.
    key    = "terraform.tfstate"
    region = "ap-south-1" #Mention specific region where tfstate bucket resides 
  }
}

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.15.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1.0"
    }
  }
}



provider "aws" {
  region  = "ap-south-1"
  access_key = AWS_ACCESS_KEY_ID
  secret_key = AWS_SECRET_ACCESS_KEY
}

provider "random" {}

variable "email" {
  default = ""
}

##IAM

resource "aws_iam_role" "common_iam_role" {
  name = "common_iam_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["ec2.amazonaws.com", "lambda.amazonaws.com"]
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "common_iam_role_policy_attachment" {
  role       = aws_iam_role.common_iam_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

##S3 for loading data

resource "random_pet" "bucket_name" {
  length    = 2
  separator = "-"
}

resource "aws_s3_bucket" "my_bucket" {
  bucket = "${random_pet.bucket_name.id}-test_data"

  tags = {
    Name        = "${random_pet.bucket_name.id}-test_data"
    Environment = "Dev"
  }
}


##SNS

resource "random_pet" "sns_name" {
  length    = 2
  separator = "-"
}

resource "aws_sns_topic" "my_topic" {
  name = "${random_pet.sns_name.id}-sns-topic"
}

resource "aws_sns_topic_subscription" "my_topic_subscription" {
  topic_arn = aws_sns_topic.my_topic.arn
  protocol  = "email"
  endpoint  = var.email
}

##Lambda

resource "aws_lambda_function" "lambda_function" {
  function_name = "notifysns"
  role          = aws_iam_role.common_iam_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.9"
  filename      = "lambda_function.zip"

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.my_topic.arn
    }
  }

  tags = {
    Name = "notifysns"
  }
}


resource "aws_lambda_function_event_invoke_config" "destination_config" {
  function_name = aws_lambda_function.lambda_function.function_name
  destination_config {
    on_success {
      destination = aws_sns_topic.my_topic.arn
    }
  }
}


output "sns_topic_arn" {
  value = aws_sns_topic.my_topic.arn
}

output "lambda_function_arn" {
  value = aws_lambda_function.lambda_function.arn
}

output "sns_topic_name" {
  value = aws_sns_topic.my_topic.name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.my_bucket.bucket
}

output "lambda_function_name" {
  value = aws_lambda_function.lambda_function.function_name
}
