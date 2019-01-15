#!/usr/bin/env python
import os
import boto3

s3Client = boto3.client('s3')
buckets = s3Client.list_buckets()
DAYS = int(os.environ['DAYS'])

def setType(key):
  if key == "NoncurrentVersionTransitions":
    return "NoncurrentDays"
  else:
    return "Days"

# changes incoming rule to be DAYS
def changeRule(rule, rule_key):
  type = setType(key)
  rule[rule_key][0][type] = DAYS
  return rule

def verifyRule(rule, key):
  type = setType(key)
  if rule['Status'] == 'Enabled':
    for rule_key in rule:
      if rule_key == key:
        for transition in rule[key]:
          if transition['StorageClass'] == 'INTELLIGENT_TIERING' and transition[type] != DAYS:
            # rule is bad, need to change rule
            return True
  # rule is good, no need for action
  return False

def newRule(key):
  type = setType(key)
  rule = {
          'Filter': { 'Prefix': '' },
          'Status': 'Enabled',
          key: [{ type: DAYS, 'StorageClass': 'INTELLIGENT_TIERING' }]
          }
  return rule

def checkForRule(listOfRules, key):
  type = setType(key)
  for rule in listOfRules:
    if rule['Status'] == 'Enabled':
      for rule_key in rule:
        if rule_key == key:
          for transition in rule[key]:
            if transition['StorageClass'] == 'INTELLIGENT_TIERING' and transition[type] == DAYS:
              # rule is good, no need for action
              return False
  # rule is missing, create rule action is needed
  return True

def s3SetIntelligentTiering(event, context):
  for bucket in buckets['Buckets']:
    print(bucket['Name'])

    # check versioning status of bucket
    try:
      if s3Client.get_bucket_versioning(Bucket=bucket['Name'])['Status']:
        versioningEnabled = True
    except:
      versioningEnabled = False

    # if there is no lifecycle policy set, set up a default one.
    try:
      dictOf = s3Client.get_bucket_lifecycle_configuration(Bucket=bucket['Name'])
    except:
      listOf = []
      if versioningEnabled:
        listOf.append(newRule('NoncurrentVersionTransitions'))
      listOf.append(newRule('Transitions'))
      response = s3Client.put_bucket_lifecycle_configuration(Bucket=bucket['Name'], LifecycleConfiguration={'Rules': listOf})
      print("New lifecycle: ", response)
      continue

    if versioningEnabled:
      keys = ["NoncurrentVersionTransitions", "Transitions"]
    else:
      keys = ["Transitions"]

    for key in keys:
      # looks at existing rules, fixing if needed
      # using range instead of basic list comprehension because we need to pass
      # the rule number into the changeRule function so that we update the correct one
      for ruleNum in range(len(dictOf['Rules'])):
        if verifyRule(dictOf['Rules'][ruleNum], key):
          dictOf['Rules'][ruleNum] = changeRule(dictOf['Rules'][ruleNum], key)
          response = s3Client.put_bucket_lifecycle_configuration(Bucket=bucket['Name'], LifecycleConfiguration={'Rules': dictOf['Rules']})
          print("Fixing rule response: ", response)

    # looks for existance of rule, creating if needed
    if checkForRule(dictOf['Rules'], key):
      dictOf['Rules'].append(newRule(key))
      response = s3Client.put_bucket_lifecycle_configuration(Bucket=bucket['Name'], LifecycleConfiguration={'Rules': dictOf['Rules']})
      print("Creating rule response: ", response)
