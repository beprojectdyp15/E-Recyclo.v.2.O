import re

filepath = r'b:\E-RECYCLO\RECYCLO.v2.O\templates\accounts\complete_collector_profile.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# We only have one page_content block, but there's a small issue with how it was inserted if there are duplicate endblocks from multiple replacements.
# Let's count block / endblocks

blocks = re.findall(r'{%\s*block\s+(\w+)\s*%}', content)
endblocks = re.findall(r'{%\s*endblock\s*%}', content)
print("Blocks:", len(blocks))
print("Endblocks:", len(endblocks))
