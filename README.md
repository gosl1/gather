# gather

A small command-line tool that collects files into a folder based on **file type**, **name pattern**, and/or a **time interval**.

It works on Windows, macOS, and Linux. It needs Python 3.9 or newer and no extra packages.

## Quick start

```
python gather.py school_pdf --ext pdf --name CMSC --source ~/Downloads --dry-run
```

This looks in `~/Downloads` for PDFs whose name contains "CMSC" and shows what it *would* move into `~/Downloads/school_pdf`. Remove `--dry-run` to actually do it.

## Usage

```
python gather.py DEST [options]
```

`DEST` is the folder the files go into.

- A plain name like `school_pdf` is created inside the source folder.
- An absolute path like `D:\Backup\school` or `/home/me/school` is used as-is.
- The folder is created automatically if it doesn't exist.

### Options

| Option | Meaning |
|---|---|
| `-s`, `--source FOLDER` | Folder to scan. Default: the current directory. |
| `-r`, `--recursive` | Also scan subfolders. |
| `-e`, `--ext EXT [EXT ...]` | File extensions, e.g. `pdf docx pptx`. The dot is optional and case doesn't matter. |
| `-n`, `--name REGEX` | A regular expression searched in the file name. Can be repeated. |
| `-g`, `--glob PATTERN` | A shell-style pattern on the file name, e.g. `*CMSC*`. Can be repeated. |
| `-x`, `--exclude REGEX` | Skip files whose name matches this regex. Can be repeated. |
| `--start TIME` | Earliest time. Format: `YYYY-MM-DD` or `"YYYY-MM-DD HH:MM"`. |
| `--end TIME` | Latest time, inclusive. A date-only value covers that whole day. |
| `--by modified\|created` | Which timestamp `--start` and `--end` use. Default: `modified`. |
| `-c`, `--case-sensitive` | Make name matching case-sensitive. Default is case-insensitive. |
| `--copy` | Copy files instead of moving them. |
| `-d`, `--dry-run` | Print what would happen without changing anything. |

You must give at least one filter (`--ext`, `--name`, `--glob`, `--start`, or `--end`). This stops you from accidentally moving every file in a folder.

## How filters combine

- **Different filters are combined with AND.** A file must pass every filter you gave.
- **Several values for the same filter are combined with OR.** `--ext pdf docx` matches PDFs or Word files. `--name CMSC --name STAT` matches names containing either.
- `--exclude` always removes a file, even if it matched everything else.

Example: `--ext pdf --name CMSC --start 2026-08-01` means "a PDF, with CMSC in its name, from August 1 onward".

## Examples

Take every file with `CMSC` in its name:

```
python gather.py cmsc_files --name CMSC --source ~/Downloads
```

Take PDFs and slides from a date range into a folder somewhere else:

```
python gather.py ~/Documents/school --ext pdf pptx --start 2026-08-01 --end 2026-10-19 --source ~/Downloads
```

Take every file from the last few hours of a specific day:

```
python gather.py today_files --start "2026-10-19 08:00" --end "2026-10-19 17:30"
```

Match several courses at once with one regex:

```
python gather.py school --name "CMSC|STAT|MATH" --ext pdf
```

Match names like `lab1`, `Lab02`, `LAB_3` at the start of the name:

```
python gather.py labs --name "^lab_?\d+"
```

Same idea using a glob instead of a regex:

```
python gather.py labs --glob "lab*"
```

Everything with CMSC in the name except drafts:

```
python gather.py cmsc_files --name CMSC --exclude "draft|old"
```

Make a backup copy instead of moving, searching subfolders too:

```
python gather.py backup_pdfs --ext pdf --recursive --copy
```

Match by when the file was created instead of last changed:

```
python gather.py new_stuff --start 2026-10-01 --by created
```

## Regex quick reference

Names are searched with Python's `re.search`, so a pattern matches if it appears *anywhere* in the file name.

| Pattern | Matches |
|---|---|
| `CMSC` | any name containing "CMSC" |
| `^CMSC` | names that start with "CMSC" |
| `\.pdf$` | names that end with ".pdf" |
| `CMSC\s?\d{3}` | "CMSC131", "CMSC 131" |
| `CMSC|STAT` | names containing either word |
| `lab_?\d+` | "lab1", "lab_12" |

Tips:

- On Windows PowerShell, wrap patterns containing `|`, `^`, or `\` in quotes.
- If regex feels like too much, `--glob "*CMSC*"` does the same simple "contains" match.

## Good to know

- **Name collisions:** if a file with the same name is already in the destination, the new one is renamed to `name (1).ext`, `name (2).ext`, and so on. Nothing is overwritten.
- **The destination is skipped:** files already inside the destination folder are never picked up again, even with `--recursive`.
- **Timestamps:** `modified` is the last time the file's contents changed. `created` is the creation time on Windows and macOS. On Linux creation time isn't stored, so `created` falls back to `modified`.
- **Copying keeps timestamps:** `--copy` preserves each file's original modified time.
- **Preview first:** use `--dry-run` whenever you're trying a new combination of filters.

## Optional: run it from anywhere

On macOS or Linux:

```
chmod +x gather.py
sudo cp gather.py /usr/local/bin/gather
gather school --ext pdf --name CMSC
```

On Windows, put `gather.py` in a folder that is on your PATH and run it with `python gather.py ...`, or create a `gather.bat` file next to it containing:

```
@python "%~dp0gather.py" %*
```