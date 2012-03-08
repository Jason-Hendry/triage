from pyramid.view import view_config
from pyramid.renderers import render_to_response
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from jinja2 import Markup

from triage.util import Paginator
from triage.models import Error, Comment, Tag, User
from triage.forms import CommentsSchema, TagSchema
from deform import Form, ValidationFailure
from time import time


def get_errors(request):
    available_projects = request.registry.settings['projects']
    selected_project = get_selected_project(request)

    search = request.GET.get('search', '')
    show = request.GET.get('show', 'open') # open, resolved, mine
    tags = request.GET.getall('tags')
    order_by = request.GET.get('order_by', 'date')
    direction = request.GET.get('direction', 'desc')
    start = request.GET.get('start', 0)
    end = start + 20

    if show not in ['open', 'resolved', 'mine']:
        show = 'open'

    if show == 'open':
        errors = Error.objects.active(selected_project)
    elif show == 'resolved':
        errors = Error.objects.resolved(selected_project)
    elif show == 'mine':
        errors = Error.objects.active(selected_project).filter(claimedby=request.user)

    if search:
        errors.search(search)

    if tags:
        errors.filter(tags__in=tags)
 
    order_map = {
        'date': 'timelatest',
        'occurances': 'count',
        'activity': 'comments'
    }

    if order_by in order_map:
        order_by = order_map[order_by]
    else:
        order_by = 'timelatest'

    if direction == 'desc':
        order_by = '-' + order_by
    
    return errors.order_by(order_by)[start:end]
    

@view_config(route_name='error_list', permission='authenticated', xhr=True, renderer='errors/list.html')
def error_list(request):
    return {
        'selected_project': get_selected_project(request),
        'errors': get_errors(request)
    }


@view_config(route_name='error_list', permission='authenticated', xhr=False, renderer='error-list.html')
def error_page(request):
    available_projects = request.registry.settings['projects']
    selected_project = get_selected_project(request)

    search = request.GET.get('search', '')
    show = request.GET.get('show', 'open') # open, resolved, mine
    tags = request.GET.getall('tags')
    order_by = request.GET.get('order_by', 'date')
    direction = request.GET.get('direction', 'desc')    
    start = request.GET.get('start', 0)
    end = start + 20

    if show not in ['open', 'resolved', 'mine']:
        show = 'open'

    errors = get_errors(request)

    page = request.params.get('page', '1')
    paginator = Paginator(errors, size_per_page=20, current_page=page)
    return {
        'search': search,
        'errors': paginator.get_current_page(),
        'paginator': paginator,
        'selected_project': selected_project,
        'available_projects': available_projects,
        'show': show,
        'order_by': order_by,
        'direction': direction,
        'tags': Tag.objects(),
        'users': User.objects(),
    }



@view_config(route_name='error_view', permission='authenticated')
def view(request):
    available_projects = request.registry.settings['projects']
    selected_project = get_selected_project(request)

    error_id = request.matchdict['id']
    try:
        error = Error.objects(project=selected_project['id']).with_id(error_id)
    except:
        return HTTPNotFound()

    comment_schema = CommentsSchema()
    comment_form = Form(comment_schema, buttons=('submit',), formid="comment_form")

    tag_schema = TagSchema()
    tag_form = Form(tag_schema, buttons=('submit',), formid="tag_form")

    if 'submit' in request.POST:
        form_id = request.POST['__formid__']
        controls = request.POST.items()

        if form_id == 'comment_form':
            try:
                values = comment_form.validate(controls)

                error.comments.append(Comment(
                    author=request.user,
                    content=values['comment'],
                    created=int(time())
                ))
                error.save()

                url = request.route_url('error_view', project=selected_project['id'], id=error_id)
                return HTTPFound(location=url)
            except ValidationFailure, e:
                comment_form_render = e.render()
        elif form_id == 'tag_form':
            try:
                values = tag_form.validate(controls)

                # build a list of comma seperated, non empty tags
                tags = [t.strip() for t in values['tag'].split(',') if t.strip() != '']

                changed = False
                for tag in tags:
                    if tag not in error.tags:
                        error.tags.append(tag)
                        changed = True
                        Tag.create(tag).save()

                if changed:
                    error.save()

                url = request.route_url('error_view', project=selected_project['id'], id=error_id)
                return HTTPFound(location=url)
            except ValidationFailure, e:
                tag_form_render = e.render()

    if request.user not in error.seenby:
        error.seenby.append(request.user)
        error.save()

    params = {
        'error': error,
        'instance': error.instances[-1],
        'other_errors': error.instances,
        'selected_project': selected_project,
        'available_projects': available_projects,
        'comment_form': comment_form,
        'tag_form': tag_form,
    }

    try:
        template = 'error-view/' + str(error['language']).lower() + '.html'
        return render_to_response(template, params)
    except:
        template = 'error-view/generic.html'
        return render_to_response(template, params)


@view_config(route_name='error_toggle_claim', permission='authenticated')
def toggle_claim(request):
    error_id = request.matchdict['id']
    selected_project = get_selected_project(request)

    try:
        error = Error.objects(project=selected_project['id']).with_id(error_id)
        error.claimedby = None if error.claimedby else request.user
        error.save()

        url = request.route_url('error_view', project=selected_project['id'], id=error_id)
        return HTTPFound(location=url)
    except:
        return HTTPNotFound()


@view_config(route_name='error_toggle_hide')
def toggle_hide(request):
    error_id = request.matchdict['id']
    selected_project = get_selected_project(request)

    try:
        error = Error.objects(project=selected_project['id']).with_id(error_id)
        error.hiddenby = None if error.hiddenby else request.user
        error.save()

        url = request.route_url('error_view', project=selected_project['id'], id=error_id)
        return HTTPFound(location=url)
    except:
        return HTTPNotFound()


def get_selected_project(request):
    selected_project_key = request.matchdict['project']
    available_projects = request.registry.settings['projects']

    if selected_project_key in available_projects:
        return available_projects[selected_project_key]
    else:
        raise HTTPNotFound()
