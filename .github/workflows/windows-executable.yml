name: Windows executable

on:
  workflow_dispatch:
  push:
    branches: [main]
    tags: ["v*"]
  pull_request:

permissions:
  contents: write

jobs:
  build-windows:
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: requirements-build.txt

      - name: Install build tools
        run: python -m pip install -r requirements-build.txt

      - name: Run tests
        run: python -m unittest discover -s tests -v

      - name: Build graphical executable
        run: pyinstaller --noconfirm --clean ElementChess.spec

      - name: Package executable
        shell: pwsh
        run: Compress-Archive -Path dist/ElementChess.exe -DestinationPath ElementChess-Windows-x64.zip

      - name: Publish workflow artifact
        uses: actions/upload-artifact@v4
        with:
          name: ElementChess-Windows-x64
          path: ElementChess-Windows-x64.zip
          if-no-files-found: error

      - name: Attach executable to tagged release
        if: startsWith(github.ref, 'refs/tags/v')
        shell: pwsh
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          $tag = "${{ github.ref_name }}"
          gh release view $tag *> $null
          if ($LASTEXITCODE -eq 0) {
            gh release upload $tag ElementChess-Windows-x64.zip --clobber
          } else {
            gh release create $tag ElementChess-Windows-x64.zip --generate-notes --title "ElementChess $tag"
          }
