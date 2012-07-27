from jinja2 import evalcontextfilter, Markup
import datetime
import time
@evalcontextfilter
def github_link(eval_ctx, value):
    if 'file' in value:
        path = str(value['file'])
        line = str(value['line'])
        shortPath = path.replace('/mnt/hgfs/projects/contests/', '')

        github = path.replace('/mnt/hgfs/projects/contests/', 'https://github.com/99designs/contests/tree/production/')

        result = '<a href="' + github + '#L' + line + '" target="_blank">' + shortPath + ':' + line + '</a>'

        if eval_ctx.autoescape:
            result = Markup(result)
        return result

    return ''

@evalcontextfilter
def relative_date(eval_ctx, timestamp):
    def prettydate(d):
        diff = datetime.datetime.now() - d
        s = diff.seconds
        if diff.days > 7 or diff.days < 0:
            return d.strftime('%d %b %y')
        elif diff.days == 1:
            return '1 day ago'
        elif diff.days > 1:
            return '{} days ago'.format(diff.days)
        elif s <= 1:
            return 'just now'
        elif s < 60:
            return '{} seconds ago'.format(s)
        elif s < 120:
            return '1 min ago'
        elif s < 3600:
            return '{} mins ago'.format(s / 60)
        elif s < 7200:
            return '1 hr ago'
        else:
            return '{} hrs ago'.format(s / 3600)
    return timestamp
    return prettydate(timestamp)
