import os
from os.path import join
from shutil import rmtree, copytree

from invoke import Collection, task
from invocations.docs import docs, www, sites
from invocations.packaging.release import ns as release_coll, publish


@task
def test(ctx, verbose=True, coverage=False, opts=""):
    # TODO: once pytest coverage plugin works, see if there's a pytest-native
    # way to handle the env stuff too, then we can remove these tasks entirely
    # in favor of just "run pytest"?
    if verbose:
        opts += " --verbose"
    runner = "pytest"
    if coverage:
        # Leverage how pytest can be run as 'python -m pytest', and then how
        # coverage can be told to run things in that manner instead of
        # expecting a literal .py file.
        # TODO: get pytest's coverage plugin working, IIRC it has issues?
        runner = "coverage run --source=paramiko -m pytest"
    # Strip SSH_AUTH_SOCK from parent env to avoid pollution by interactive
    # users.
    env = dict(os.environ)
    if 'SSH_AUTH_SOCK' in env:
        del env['SSH_AUTH_SOCK']
    cmd = "{} {}".format(runner, opts)
    # NOTE: we have a pytest.ini and tend to use that over PYTEST_ADDOPTS.
    ctx.run(cmd, pty=True, env=env, replace_env=True)


@task
def coverage(ctx, opts=""):
    return test(ctx, coverage=True, opts=opts)


# Until we stop bundling docs w/ releases. Need to discover use cases first.
# TODO: would be nice to tie this into our own version of build() too, but
# still have publish() use that build()...really need to try out classes!
@task
def release(ctx, sdist=True, wheel=True, sign=True, dry_run=False):
    """
    Wraps invocations.packaging.publish to add baked-in docs folder.
    """
    # Build docs first. Use terribad workaround pending invoke #146
    ctx.run("inv docs", pty=True, hide=False)
    # Move the built docs into where Epydocs used to live
    target = 'docs'
    rmtree(target, ignore_errors=True)
    # TODO: make it easier to yank out this config val from the docs coll
    copytree('sites/docs/_build', target)
    # Publish
    publish(ctx, sdist=sdist, wheel=wheel, sign=sign, dry_run=dry_run)
    # Remind
    print("\n\nDon't forget to update RTD's versions page for new minor "
          "releases!")


# TODO: "replace one task with another" needs a better public API, this is
# using unpublished internals & skips all the stuff add_task() does re:
# aliasing, defaults etc.
release_coll.tasks['publish'] = release

ns = Collection(test, coverage, release_coll, docs, www, sites)
ns.configure({
    'packaging': {
        # NOTE: many of these are also set in kwarg defaults above; but having
        # them here too means once we get rid of our custom release(), the
        # behavior stays.
        'sign': True,
        'wheel': True,
        'changelog_file': join(
            www.configuration()['sphinx']['source'],
            'changelog.rst',
        ),
    },
})
