{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python314
    uv
  ];

  shellHook = ''
    export UV_PYTHON_DOWNLOADS=never
    export UV_PROJECT_ENVIRONMENT=venv
    uv sync --no-dev --extra cli --python ${pkgs.python314}/bin/python \
      && source venv/bin/activate \
      && clear && bugpipe -h
  '';
}
