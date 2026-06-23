import re

with open('api_docs.md', 'r') as f:
    api_docs = f.read()

with open('README.md', 'r') as f:
    readme = f.read()

# Replace everything from "### API Endpoints" up to "---" or "## "
pattern = r"### API Endpoints\n.*?---"
new_readme = re.sub(pattern, "### API Endpoints\n\n" + api_docs + "\n---", readme, flags=re.DOTALL)

with open('README.md', 'w') as f:
    f.write(new_readme)
