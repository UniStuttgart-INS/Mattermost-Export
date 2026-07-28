# Mattermost-Export

A simple Python script that exports Mattermost chat data to various formats via the Mattermost API.
This is a fork of https://github.com/alallier/Mattermost-Export with minor adaptions.

## Usage

The project is using the [`uv`](https://docs.astral.sh/uv/) package and project manager. After cloning you can simply use the command 
```shell
uv run MMExport2PDF.py <OPTIONS>
```

Run 
```shell
uv run MMExport2PDF.py --help
```
to see a a full list of the command line arguments and options.

To e.g. export all channels from a server `<SERVER>` of user `<USER>` and team `<TEAM>` including images (`-i`) and files (`-f`) you can use
```shell
uv run MMExport2PDF.py --server=<SERVER> --auth=<MMAUTHTOKEN> --user=<USER> --team=<TEAM> -i -f
```
The `<MMAUTHTOKEN>` can be obtained by logging into the Mattermost instance using a browser and reading out the token from the developer console.
E.g. for Firefox:
1. Log in
2. Press `F12`
3. Navigate to `Storage`
4. Under `Cookies` ➜ `https://<URL_OF_YOUR_SERVER>` you should see a cookie named `MMAUTHTOKEN`. The value is the string you need to enter in the command above.
