Copy the `config` file as ~/.list_archive (or just leave it in the current path), modify
it to include all mailing lists you want to search in, change the `name` and `email` items
in `general` section to the person you want to query. Then run the example command, you
will get a basic statics on the person's activities on the mailing lists during July, 2016.

Example command:

    ./main.py --year 2016 --month 6
