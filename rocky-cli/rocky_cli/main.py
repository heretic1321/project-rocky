"""rocky-cli — control Rocky the quadruped robot from the terminal."""

import click
import requests

from rocky_cli.client import RockyClient, DEFAULT_ROBOT_URL

MOVEMENTS = [
    "forward", "backward", "left", "right", "stop",
    "rest", "stand", "wave", "dance", "swim", "point",
    "pushup", "bow", "cute", "freaky", "worm", "shake",
    "shrug", "dead", "crab",
]

FACES = [
    "walk", "rest", "stand", "dance", "wave",
    "happy", "sad", "angry", "surprised", "sleepy",
    "love", "excited", "confused", "thinking",
    "talk_happy", "talk_sad", "talk_angry", "talk_surprised",
    "talk_sleepy", "talk_excited", "talk_confused", "talk_thinking",
    "idle", "idle_blink", "default",
]


def get_client(ctx: click.Context) -> RockyClient:
    return ctx.obj["client"]


@click.group()
@click.option("--url", default=DEFAULT_ROBOT_URL, envvar="ROCKY_URL",
              help="Robot base URL (default: http://192.168.4.1)")
@click.pass_context
def cli(ctx, url):
    """Control Rocky the quadruped robot over WiFi."""
    ctx.ensure_object(dict)
    ctx.obj["client"] = RockyClient(url)


@cli.command()
@click.argument("action", type=click.Choice(MOVEMENTS, case_sensitive=False))
@click.pass_context
def move(ctx, action):
    """Send a movement command to Rocky."""
    client = get_client(ctx)
    try:
        result = client.move(action)
        click.echo(f"Rocky: {action} — {result.get('message', 'ok')}")
    except requests.ConnectionError:
        click.echo("Error: Cannot reach Rocky. Are you on the Sesame-Controller WiFi?", err=True)
    except requests.RequestException as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("expression", type=click.Choice(FACES, case_sensitive=False))
@click.pass_context
def face(ctx, expression):
    """Change Rocky's OLED face expression."""
    client = get_client(ctx)
    try:
        result = client.face(expression)
        click.echo(f"Rocky face: {expression} — {result.get('message', 'ok')}")
    except requests.ConnectionError:
        click.echo("Error: Cannot reach Rocky. Are you on the Sesame-Controller WiFi?", err=True)
    except requests.RequestException as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def status(ctx):
    """Get Rocky's current status."""
    client = get_client(ctx)
    try:
        s = client.status()
        click.echo(f"Command:  {s.get('currentCommand', 'none')}")
        click.echo(f"Face:     {s.get('currentFace', 'none')}")
        click.echo(f"AP IP:    {s.get('apIP', 'unknown')}")
        net = s.get("networkIP")
        if net:
            click.echo(f"Net IP:   {net}")
    except requests.ConnectionError:
        click.echo("Error: Cannot reach Rocky. Are you on the Sesame-Controller WiFi?", err=True)
    except requests.RequestException as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument("cmd")
@click.option("--face", "-f", default=None, help="Face to show alongside command")
@click.pass_context
def send(ctx, cmd, face):
    """Send a raw command (and optional face) to Rocky."""
    client = get_client(ctx)
    try:
        result = client.command(cmd=cmd, face=face)
        click.echo(f"Rocky: {result.get('message', 'ok')}")
    except requests.ConnectionError:
        click.echo("Error: Cannot reach Rocky. Are you on the Sesame-Controller WiFi?", err=True)
    except requests.RequestException as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    cli()
