Copy .py files into directory, make main.py executable.

If you want to use config file, place it as ~/.list_archive
    Example config file:

    [general]
    name = My Name
    email = email1@example.com,another@mail.com
    year = 2016
    month = 7

    [LKML]

    [RH]
    lists = list-name1,list-2,another-list

Include [lkml] if you want to search LKML, and include all Red Hat internal
listsn into [RH] lists option. If you want to specify more emails or Red Hat
lists, divide them only with ','

When using config file, run main.py without any arguments (eg ./main.py). If you
want to use a single command without config, you need to include all options.
    Example command:

    ./main.py --name "My Name" --email email1@example.com another@mail.com \
    --year 2016 --month 7 lkml rhel-list1 rhel-list2

You can specify more emails (like in the example) after the --email option.
Include 'lkml' string if you wish to search LKML archives. All other
unidentified strings are counted as Red Hat mailing lists.
