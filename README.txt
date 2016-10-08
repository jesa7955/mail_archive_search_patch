Copy .py files into directory, make main.py executable.

Copy the `config` file as ~/.list_archive (or just leave it in the current path
when you are testing), modify it to include all mailing lists you want to 
search, change the `name` and `email` items in `general` section to the person 
you want to query. Then run the example command, you will get a basic statisics
on the person's activities on the mailing lists during Auguest, 2016.

Example command:

    ./main.py --year 2016 --month 8

You can also query another one's status on mailing lists specified in the config
file by simply appending --name and --email command line arguments, like:

    ./main.py --year 2016 --month 8 --name foo --email bar@test.com

Notes:

1. When there are two threads which have the same subject appear in different dates, e.g.
one reply the same thread in different days, only the latest date will be printed.

    examples:

        2016-09-07 Re: [PATCH v1] kdump, vmcoreinfo: report memory sections virtual addresses
        2016-09-13 Re: [PATCH v1] kdump, vmcoreinfo: report memory sections virtual addresses

        will be displayed as

    [2] 2016-09-13 Re: [PATCH v1] kdump, vmcoreinfo: report memory sections virtual addresses

