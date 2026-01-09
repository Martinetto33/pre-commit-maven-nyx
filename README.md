# pre-commit-maven-nyx
A pre-commit githook that checks if the pom.xml version matches with the Nyx computed version and only allows commits if such check passes.

## Prerequisites

### Semantic versioning and release

This guide assumes you want to use semantic versioning and release, and therefore that you are familiar with such concepts and with conventional commits.

### Nyx

Install Nyx: https://github.com/mooltiverse/nyx/releases/latest. It's a tool for semantic versioning and release.
You can use it from the CLI once you add the executable to your PATH.

This guide refers to **Nyx version [3.1.7](https://github.com/mooltiverse/nyx/releases/tag/3.1.7)**.

You will need to configure Nyx to generate a state file. Below is an example
configuration that is able to infer the new version, generate a changelog and
save the state file in the root of your project, named `nyx-state.json`.

#### Configuration for Nyx

In a `.nyx` folder that you can track for version control, create a `changelog.hbs` template file, which will be used in the creation of the templates.
Put the following content in the file, after replacing LINK-TO-YOUR-REPO with the link to your `git` repository:

```handlebars
{{!-- Template file for changelog generation --}}
# [__VERSION__] - Changelog <span style="color: darkgray; font-size: medium; font-style: italic">(__DATE__)</span>
{{#releases}}
{{#sections}}
## {{name}}
{{#commits}}
* [[{{#short5}}{{sha}}{{/short5}}]](https://LINK-TO-YOUR-REPO/commit/{{sha}}) {{message.fullMessage}} <span style="color: #11daf5">({{authorAction.identity.name}})</span>
{{/commits}}
{{/sections}}
{{/releases}}
```

Then, *in the root of your project*, create a `.nyx.yaml` configuration file with the following content:

```yaml
---
preset: simple

changelog:
  path: "CHANGELOG.md"
  template: ".nyx/changelog.hbs"
  # Feel free to add more sections to the changelog, as long
  # as they have matching conventional commits associated.
  # For example, a "Style changes": "^style$" rule can be
  # added to document UI changes.
  sections:
    "Added": "^feat$"
    "Fixed": "^fix$"
    "Build changes": "^build$"
    "CI changes": "^ci$"

stateFile: "nyx-state.json" # needed to store the version number somewhere

substitutions:
  enabled:
    - versionToken
    - dateToken
  items:
    versionToken:
      files: "CHANGELOG.md"
      match: "__VERSION__" # this token was decided arbitrarily; it avoids weird metadata in the version name
      replace: "{{versionMajorNumber}}.{{versionMinorNumber}}.{{versionPatchNumber}}"
    dateToken:
      files: "CHANGELOG.md"
      match: "__DATE__" # used to display the date of the package release
      replace: "{{#timestampISO8601}}{{timestamp}}{{/timestampISO8601}}"
```
#### Testing the configuration

To see the computed version, run

```bash
nyx --preset=simple --summary infer
```
The `current version` entry will show the computed version.

To run the changelog generation and the state file creation, which will be needed by _this_ hook, run:

```bash
nyx --c=.nyx.yaml make
```

#### More info in the official Nyx documentation

Here's the Nyx user guide: https://mooltiverse.github.io/nyx/docs/user/quick-start/.

Be warned that the guide is rather incomplete, as it doesn't provide a complete example of a working configuration.

### Python

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
