#!/bin/bash

profiles=("devkernelaccess" "devtestkernelaccess" "qakernelaccess" "stagekernelaccess" "prodkernelaccess" "sharedserviceskernelaccess" "masterkernelaccess" "awsadminkernelaccess")
# profiles=("devkernelaccess")
stackName="s3-intelligent-tiering"
s3Bucket="${stackName}-bucket"

for profile in ${profiles[@]}
do
  if [ $profile != "masterkernelaccess" ];
  then
    . awsume ${profile}
  else
    . awsume -u
  fi
  aws s3 mb s3://$s3Bucket-$profile
  sam package --template-file ./serverless.yml --output-template-file serverless-output-$profile.yml --s3-bucket $s3Bucket-$profile
  aws cloudformation deploy --template-file ./serverless-output-$profile.yml --stack-name $stackName-${profile::-12} --capabilities CAPABILITY_IAM
done
