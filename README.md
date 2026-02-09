<div align="center">
	<h1 align="center"><b>Pylings</b></h1>
</div>

<br/>

<p align="center">
  <img src="https://img.shields.io/badge/Made%20with-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Made with Python">
 <img src="https://img.shields.io/pypi/pyversions/pylings?style=for-the-badge" alt="Python Version">
 <img src="https://img.shields.io/badge/pylint-9.86-green?style=for-the-badge&logo=python&logoColor=white">
  <a href="https://pypi.org/project/pylings/">
    <img src="https://img.shields.io/pypi/v/pylings?style=for-the-badge" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/pylings/">
	<img alt="Dynamic Regex Badge" src="https://img.shields.io/badge/dynamic/regex?url=https%3A%2F%2Fstatic.pepy.tech%2Fpersonalized-badge%2Fpylings%3Fperiod%3Dtotal%26units%3DNONE&search=%3Ctext%5B%5E%3E%5D*%3E(%5Cd%2B)%3C%5C%2Ftext%3E&replace=%241&style=for-the-badge&label=Downloads">

  </a>
  <a href="https://github.com/CompEng0001/pylings/stargazers">
    <img src="https://img.shields.io/github/stars/CompEng0001/pylings?style=for-the-badge" alt="GitHub Stars">
  </a>
  <a href="https://github.com/CompEng0001/pylings/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/CompEng0001/pylings/.github/workflows/python-publish.yml?&style=for-the-badge&label=Deploy%20to%20Pip" alt="Build Status">
  </a>
  <a href="https://zenodo.org/records/17570382">
  <img src="https://img.shields.io/badge/doi-10.5281%2Fzenodo.17570382-blue?style=for-the-badge" alt="doi 10.5281/zenodo.17570382">
  
  </a>
</p> 

![](./images/pylings_demo_2.gif)

## Purpose

Pylings is an interactive Python learning tool heavily inspired by the renowned [Rustlings](https://github.com/rust-lang/rustlings). It provides small, focused exercises to help you learn Python by fixing code snippets and experimenting with them.


Pylings is designed to help beginners and experienced developers alike improve their Python skills through hands-on practice. Each exercise covers core Python concepts such as variables, data structures, loops, and more. This includes reading and responding to compiler and interpreter messages!

## Installation

### Prerequisites

- [python](https://www.python.org/downloads/) >= 3.10  installed on your system
- [Git](https://git-scm.com/downloads) (optional, for version control)

### Steps

1. Install via `pip` (preferred) :
    
    `Windows`
    ```
    py -m pip install pylings
    ```
    
    `Linux/Unix`
    ```
    pip install pylings
    ```

    or use `git` and install locally:

    ```
    git clone git@github.com:CompEng0001/pylings.git pylings-package
    cd pylings-package
    pip install .
    ```

## Working environment

### Editor

General recommendation is VS Code with the [python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) plugin. But any editor that supports python should be enough for working on the exercises.

Will run in [GitHub Codespaces](https://github.com/features/codespaces)

### Terminal

While working with Pylings, please use a modern terminal for the best user experience, especially we recommend the Windows Terminal, with Git Bash via VS Code.

The default terminal on Linux and Mac should be sufficient too.

> [!IMPORTANT]
> There are some rendering issues, with Linux based terminals and some terminal multiplexers. 

## Doing Exercises

The exercises are sorted by topic and can be found in the subdirectory `exercises/<topic>`.
For every topic, there is an additional `README.md` file with some resources to get you started on the topic.

We highly recommend that you have a look at them before you start.

Most exercises contain an error that keeps them from compiling, and it's up to you to fix it!

<div align=center>

![](./images/exercise_pending.png)

</div>

Some exercises contain tests that need to pass for the exercise to be done

<div align=center>

![](./images/exercise_finished.png)

</div>

Search for `TODO` to find out what you need to change.
Ask for hints by entering `h`


### Running Pylings

Once installed via [`pip` or `git`](#steps), navigate to a directory of your choice and run:

  
  ```
  <py,python3> -m pylings init
  ```

  or provide the path as an argument:

  ```
  <py,python3> -m pylings init --path path/to/initialise-pylings
  ``` 

  If a directory already exists with the same name you can use:

  ```
  <py,python3> -m pylings init --force [--path path/to/initialise-pylings]
  ```

  Then you can launch `pylings` in the initialised directory

  ```
  <py,python3> -m pylings
  ```

> [!TIP]
> Of course you could always add the following to your `PATH`, and you call `pylings` directly: 
> - `Windows`
>   - `$HOME/AppData/Local/Programs/Python/Python313/`
> - `Linux`
>   -  `$HOME/.local/bin`

### Commands/Arguments
Pylings v1.1.0 supports additional developer-friendly commands:
- `update [--path path/to/initialised-pylings]` updates the workspace with the current version:
  - Useful after upgrading Pylings via `pip install --upgrade pylings`
  - Defaults to the current working directory (`cwd`)
  - Adds new exercises and removes obsolete ones from the workspace

    ![](./images/pylings_update.png)

- `run`, starts pylings from a specific exercise:
  - `pylings run exercises/01_variables/variables1.py`
  - Triggers welcome message if it's your first time
- `dry-run`, executes an exercise non-interactively:
  - `pylings dry-run 01_variables/variables1.py`
  - Accepts paths with or without the `exercises/` prefix
  - Use `--source workspace` (default) to run from local files
  - Use `--source package` to run the exercise bundled with the installed Pylings package
- `reset`, resets an exercise non-interactively:
  - `pylings reset exercises/01_variables/variables1.py`
- `sol`, executes a solution file non-interactively:
  - `pylings solution 01_variables/variables1.py`
  - Accepts paths with or without the `solutions/` prefix
  - `--source package` (default) uses installed Pylings files
  - `--source workspace` runs your own solution from the local workspace
- `--debug`, enables debug logging for advanced output, log file is workspace `.pylings_debug.log`
- `-v`, `--version`, displays version, license, and repository link
- `-h`, `--help`, shows usage info for all commands


### List mode

You can open an interactive list of all exercises by pressing `l` after launching `pylings`

- See the status of all exercises (done or pending)
- `s`: Continue at selected exercise, allowing you to tempoarily skipping exercises or revisitng a previous one
- `r`: Resets the current selected exercise back to its pending state, live!
- `c`: Checks all exercises and updates the state, incase you modify outside of pylings.

See the footer of the list for all possibilities. 

<div align=center>

![](./images/exercise_list.png)

</div>

## Themes

As of v1.2.0 you can set a theme. Currently there are two ways, builtin or custom

- Builtin:
  - `default`
  - `dark`
  - `high_contrast`
  - `catppuccin_mocha`
  - `catppuccin_macchiato`
  - `gruvbox_dark`
  - `onedark`
  - `solarized_dark`
  - `nord`
  - `tender`
  
- Custom
  - `custom`

The following fields are available for customising: 

```toml
[theme]
name = "default" # default is a builtin, change from list above, or change the values below using "custom"
GREEN = "bold green"
RED = "bold red"
ORANGE = "bold orange"
LIGHT_BLUE = "bold lightblue"
BACKGROUND = "#1e1e2e"
```

>[!NOTE]
> - If you have updated to `v1.2.0`, you will need to add the above in manually, luckily, the `default` will load
> - Use HEX colours or refer to: https://textual.textualize.io/styles/color/#syntax
> - For font styling refer to: https://textual.textualize.io/styles/text_style/

## Contributing

See [CONTRIBUTING.md](https://github.com/CompEng0001/pylings/blob/main/CONTRIBUTING.md) 🔗

Contributions are welcome! Feel free to open issues or submit pull requests.

## License

This project is licensed under the [MIT License](./LICENSE.md).

## Author

[CompEng0001](https://git@github.com/CompEng0001)
