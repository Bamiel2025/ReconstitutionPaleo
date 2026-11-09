import re, sys, html
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
print('LONGUEUR', len(s))
print('=== BALISES SCRIPT ===')
for m in re.findall(r'<script[^>]*>', s):
    print(m[:300])
print('=== LIENS / STYLES ===')
for m in re.findall(r'<link[^>]*>', s):
    print(m[:250])
print('=== APRES </style> (corps + js) ===')
i = s.find('</style>')
print(s[i:i + 30000])
