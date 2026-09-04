import glob, re

for f in glob.glob('tests/test_*.py'):
    content = open(f, 'r').read()
    content = content.replace("    app.config['TESTING'] = True\n", "")
    content = content.replace("    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'\n", "")
    open(f, 'w').write(content)
    print(f"Fixed {f}")
