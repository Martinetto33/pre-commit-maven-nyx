# pre-commit-maven-nyx
A pre-commit githook that checks if the pom.xml version matches with the Nyx computed version and only allows commits if such check passes.

## Prerequisites

You will need a Python installation. If you're working on Windows, you can use [scoop](https://scoop.sh/) to install it with

```bash

scoop install python

```

The installer will tell you about a created _.reg_ file. Double click and trust it to make python available system-wise.

After you install python, install pre-commit with:

```bash

pip install pre-commit

```

or alternatively with:

```bash

py -m pip install pre-commit

```

## Usage

This section explains how to adopt this plugin into your project, once you have pre-commit installed.

### Creating the JSON configuration file

You will need to create a `.pre-commit-maven-nyx.json` configuration file with the following content:

```json

{
  "protected_branches": ["master", "main", "release/*"],
  "nyx_version_file": "nyx-state.json",
  "pom_file": "pom.xml",
  "liquibase_dir": "src/main/resources/db/changelog",
  "check_maven": true,
  "check_liquibase": true
}

```

Change the configuration to match your file paths and names.

If you don't create such file, a default configuration will be used by the hook.

### Creating the pre-commit configuration file

In your project, you will need to create a `.pre-commit-config.yaml` file with the following contents:

```yaml
---
# .pre-commit-config.yaml (in your main Maven project)
repos:
  - repo: https://github.com/Martinetto33/pre-commit-maven-nyx
    hooks:
      - id: maven-nyx-version-sync

```

### Installing the dependency in your project

Once you've completed previous steps, run

```bash

pre-commit install

```
In case the above command fails, you might want to check the [troubleshooting](#Troubleshooting) section.

To run everything, you'll use:
```bash
pre-commit run --all-files
```

## <a name="Troubleshooting"></a> Troubleshooting

`pre-commit install` might fail if you have your core.hooksPath set with this message:

```bash
[ERROR] Cowardly refusing to install hooks with `core.hooksPath` set.
hint: `git config --unset-all core.hooksPath`
```

You can work around this by running (this assumes a Windows environment and PowerShell):

```powershell
# Storing old hooksPaths
$OldLocalHooksPath = git config core.hooksPath
$OldGlobalHooksPath = git config --global core.hooksPath

# Unsetting local and global hooksPath
git config --unset-all core.hooksPath
git config --global --unset-all core.hooksPath

# Installing hook
pre-commit install

# Restoring old hooksPath
git config core.hooksPath $OldLocalHooksPath
git config --global core.hooksPath $OldGlobalHooksPath
```
