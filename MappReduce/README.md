
# MappReduce

MappReduce.py


Para correrlo:
> ```Bash
user@user:~$ cat MappReduce/Example/googlebooks-eng-all-4gram-20120701-zz | python MappReduce/mapper.py | sort -k1,1 | python MappReduce/reducer.py
```
