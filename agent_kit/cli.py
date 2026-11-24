"""agent-kit: project tooling shared by coding agents (Claude Code, Codex, ...).

  agent-kit mockups init|build|check|validate|index [--design <dir>]
  agent-kit guides init|sync|check|list [names...] [--force]
  agent-kit skills sync      refresh the skills agent-kit installed in this project
"""

from pathlib import Path
import runpy
import sys

PACKAGE = Path(__file__).resolve().parent
MOCKUPS = PACKAGE / 'mockups'
SKILLS = PACKAGE / 'skills'


def run_script(path, argv):
    sys.argv = [str(path), *argv]
    sys.path.insert(0, str(path.parent))
    try:
        runpy.run_path(str(path), run_name='__main__')
    except SystemExit as exit_:
        return exit_.code or 0
    return 0


def mockups(argv):
    command, rest = (argv[0], argv[1:]) if argv else ('help', [])
    if command == 'init':
        from agent_kit import setup
        return setup.mockups_init(rest)
    scripts = {'build': ('build.py', []), 'check': ('build.py', ['--check']),
               'validate': ('validate.py', []), 'index': ('index.py', [])}
    if command not in scripts:
        print(__doc__)
        return 2
    script, extra = scripts[command]
    return run_script(MOCKUPS / script, [*extra, *rest])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(__doc__)
        return 0
    tool, rest = argv[0], argv[1:]
    if tool == 'mockups':
        return mockups(rest)
    if tool == 'guides':
        from agent_kit.guides import sync
        return sync.main(rest)
    if tool == 'skills' and rest[:1] == ['sync']:
        from agent_kit import setup
        return setup.skills_sync()
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
