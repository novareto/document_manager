import omegaconf


CONFIG = omegaconf.OmegaConf.create('''
app:

  factories:
    user: ${class:uvcreha.models.User}
    request: ${class:uvcreha.request.Request}

  env:
    session: uvcreha.test.session
    user: test.principal

  session:
    cookie_name: uvcreha.cookie
    cookie_secret: secret

  logger:
    name: uvcreha.test.logger

  assets:
    compile: True
    recompute_hashes: True
    bottom: True

  storage:
    schemas: /tmp/tt

  twilio:
     account_sid: AC0194a64ae983e980a03a0be66073d639
     auth_token: 847502a1b6aabd837be20326993b2ecd

  vhm:
     host: http://locahost:8080
''')
