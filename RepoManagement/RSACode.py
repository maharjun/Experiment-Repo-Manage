import yaml

with open('RSAKeys.yml', 'r') as Fin:
    KeyData = yaml.safe_load(Fin)
    PublicExp     = KeyData['e']
    PrivateExp    = KeyData['d']
    PublicModulus = KeyData['N']

def RSAEncode(InputInteger):
    return pow(InputInteger, PublicExp, PublicModulus)

def RSADecode(InputInteger):
    return pow(InputInteger, PrivateExp, PublicModulus)
