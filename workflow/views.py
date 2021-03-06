import os
import functools
import json
import tarfile
from threading import Thread
import traceback
import urllib

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import render
from django.template import RequestContext, loader
from django.utils import timezone
from lxml import etree
import requests
from django.views.generic.detail import DetailView
from django.utils.decorators import method_decorator
from django.views.generic.list import ListView
from django.contrib.auth.decorators import permission_required, login_required
from earkcore.models import StatusProcess_CHOICES
from django.views.decorators.csrf import csrf_exempt
from earkcore.models import InformationPackage

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from celery.result import AsyncResult
from sandbox.task_execution_xml import TaskExecutionXml
from search.models import DIP
from workers import tasks
from django.http import JsonResponse
from django.forms import ModelChoiceField
from sip2aip import forms
import urllib2
#import workers.tasks
from workers.default_task_context import DefaultTaskContext
from workers.tasks import SIPPackaging, AIPPackaging, LilyHDFSUpload, DIPAcquireAIPs, DIPExtractAIPs, AIPStore, AIPPackageMetsCreation, AIPIndexing, \
    DIPAcquireDependentAIPs, SIPtoAIPReset, AIPtoDIPReset
from workers.taskconfig import TaskConfig
from workflow.models import WorkflowModules
from workflow.models import Wirings
import json

from config.configuration import config_path_work
from earkcore.filesystem.fsinfo import path_to_dict
from config.configuration import config_path_storage

from django.utils import dateparse

import logging
from celery import chain

@login_required
def index(request):
    print request.user
    template = loader.get_template('workflow/index.html')
    context = RequestContext(request, {
    })
    return HttpResponse(template.render(context))

@login_required
def workflow_language(request):
    print request.user
    wfdefs = WorkflowModules.objects.all()
    template = loader.get_template('workflow/language.js')
    context = RequestContext(request, {
        'workflow_definitions': wfdefs
    })
    return HttpResponse(template.render(context), content_type='text/plain; charset=utf8')

def backend(request):
    """
    Backend of the wiring editor for handling POST requests.
    Methods are 'listWirings', 'saveWiring', 'deleteWiring'.
    :param request: Request
    :return: HttpResponse(status=200, "OK")
    """
    if request.method == "POST":

        try:
            data = json.loads(str(request.body))
            logging.debug("Request (JSON):\n" + json.dumps(data, indent=2))
            if data['method'] == "listWirings":
                wirings = Wirings.objects.all()
                wiringJsons = []
                # each wiring (wiring.working) is returned as a backslash escaped string (substitution variable: working),
                # therefore double quotes in "wiring.working" are backslash escaped.
                for wiring in wirings:
                    wiringJsons.append("""{ "id": "%(id)s", "name": "%(name)s", "working": "%(working)s", "language": "%(language)s" }"""
                                       % { 'name': wiring.name, 'working': (wiring.working).replace('"', '\\"'), 'language': wiring.language, 'id': wiring.id })
                jsonStr = """{"id": 1, "result": [ %(modules)s ], "error": null }""" % { 'modules': (",".join(wiringJsons)) }
                jsonObj = json.loads(jsonStr)
                logging.debug("Response (JSON):\n" + json.dumps(jsonObj, indent=2))
                return HttpResponse(jsonStr)
            if data['method'] == "saveWiring":
                name = data['params']['name']
                working = data['params']['working']
                language = data['params']['language']
                wiring = Wirings.objects.create(language=language,name=name,working=working)
                wiring.save()
            if data['method'] == "deleteWiring":
                name = data['params']['name']
                logging.debug("Delete wiring: %s" % name)
                u = Wirings.objects.get(name=name).delete()
        except Exception:
            logging.error('test', exc_info=True)
        return HttpResponse(status=200)
    else:
        pass

@login_required
def execution(request):
    if 'task_id' in request.session.keys() and request.session['task_id']:
        task_id = request.session['task_id']
    context = RequestContext(request, {
        'form': forms.PackageWorkflowModuleSelectForm()
    })
    return render_to_response('workflow/execution.html', locals(), context_instance=context)

@login_required
@csrf_exempt
def apply_workflow(request):
    data = {"success": False, "errmsg": "Unknown error"}
    try:
        print "Workflow execution"
        # selected_ip = request.POST['selected_ip']
        # print "selected_ip: " + request.POST['selected_ip']
        # selected_action = request.POST['selected_action']
        # print "selected_action: " + request.POST['selected_action']
        # if not (selected_ip and selected_action):
        #     return JsonResponse({"success": False, "errmsg": "Missing input parameter!"})
        # wfm = WorkflowModules.objects.get(pk=selected_action)
        # tc = TaskConfig(wfm.expected_status,  wfm.success_status, wfm.error_status)
        # if request.is_ajax():
        #     taskClass = getattr(tasks, wfm.identifier)
        #     print "Executing task: %s" % wfm.identifier
        #     job = taskClass().apply_async((selected_ip, tc,), queue='default')
        #     print "Task identifier: %s" % job.id
        #     data = {"success": True, "id": job.id}
        # else:
        #     data = {"success": False wfm = WorkflowModules.objects.get(pk=selected_action), "errmsg": "not ajax"}
        data = {"success": True, "id": "xyz", "myprop": "val"}
    except:
        tb = traceback.format_exc()
        logging.error(str(tb))
        data = {"success": False, "errmsg": "an error occurred!"}
        return JsonResponse(data)
    return JsonResponse(data)


@login_required
@csrf_exempt
def apply_task(request):
    """
    Execute selected task using selected information package as input. Task modules are registered in WorkflowModules.
    The identifier of a workflow module corresponds with the task's class name. The task is executed using celery's
    'apply_async' method.
    @type request: django.core.handlers.wsgi.WSGIRequest
    @param request: Request
    @rtype: django.http.JsonResponse
    @return: JSON response (task execution metadata)
    """
    data = {"success": False, "errmsg": "Unknown error"}
    try:
        selected_ip = request.POST['selected_ip']
        selected_action = request.POST['selected_action']
        if not (selected_ip and selected_action):
            return JsonResponse({"success": False, "errmsg": "Missing input parameter!"})
        # Get module description of the task to be executed from the database
        wfm = WorkflowModules.objects.get(pk=selected_action)
        logging.debug(selected_action)
        # Get the selected information package from the database
        ip = InformationPackage.objects.get(pk=selected_ip)
        if request.is_ajax():
            try:
                # Get task class from module identifier
                taskClass = getattr(tasks, wfm.identifier)
                print "Executing task %s" % taskClass.name
                # additional input parameters for the task can be passed through using the 'additional_params' dictionary.
                # IMPORTANT: if you want to use any of these parameters in the finalize() function, the task MUST return:
                # return task_context.additional_input

                #deserialize ip.additional_data json string from db
                import json
                additional_data = json.loads(ip.additional_data)

                additional_data['packagename'] = ip.packagename
                if ip.identifier != "":
                    additional_data['identifier'] = ip.identifier

                if wfm.identifier == AIPStore.__name__ or wfm.identifier == AIPIndexing.__name__:
                    additional_data['storage_dest'] = config_path_storage
                    if ip.storage_loc and ip.storage_loc != '':
                        additional_data['identifier'] = ip.identifier
                    print "Storage destination %s" % additional_data['storage_dest']

                if wfm.identifier in [DIPAcquireAIPs.__name__, DIPAcquireDependentAIPs.__name__, DIPExtractAIPs.__name__]:
                    dip = DIP.objects.get(name=ip.packagename)
                    selected_aips = {}
                    for aip in dip.aips.all():
                        selected_aips[aip.identifier] = aip.source
                    additional_data['selected_aips'] = selected_aips
                    additional_data['storage_dest'] = config_path_storage

                # on reset, the identifier is removed from context and from the information package record
                if wfm.identifier == SIPtoAIPReset.__name__ or wfm.identifier ==  AIPtoDIPReset.__name__:
                    additional_data['identifier'] = ''
                    ip.identifier = ''

                if wfm.identifier == AIPPackageMetsCreation.__name__:
                    additional_data['parent_id'] = ip.parent_identifier

                if wfm.identifier == AIPStore.__name__:
                    additional_data['parent_id'] = ip.parent_identifier
                    # the UUID tells us in which folder the parent AIPs' Mets file is located - only in the dev
                    # version of course, probably doesnt work in distributed storage
                    if len(additional_data['parent_id']) > 0:
                        additional_data['parent_path'] = InformationPackage.objects.get(identifier=ip.parent_identifier)
                    else:
                        additional_data['parent_path'] = ''

                if wfm.identifier == LilyHDFSUpload.__name__:
                    additional_data['storage_loc'] = ip.storage_loc

                # Execute task
                task_context = DefaultTaskContext(ip.uuid, ip.path, taskClass.name, None, additional_data, None)
                job = taskClass().apply_async((task_context,), queue='default')
                data = {"success": True, "id": job.id}

                # persist changes to information package object
                ip.save()
            except AttributeError, err:
                errdetail = """The workflow module '%s' does not exist.
It might be necessary to run 'python ./workers/scantasks.py' to register new or renamed tasks.""" % wfm.identifier
                data = {"success": False, "errmsg": "Workflow module '%s' does not exist" % wfm.identifier, "errdetail": errdetail}
        else:
            data = {"success": False, "errmsg": "not ajax"}
    except Exception, err:
        tb = traceback.format_exc()
        logging.error(str(tb))
        data = {"success": False, "errmsg": err.message, "errdetail": str(tb)}
        return JsonResponse(data)
    return JsonResponse(data)

@login_required
@csrf_exempt
def poll_state(request):
    """
    @type request: django.core.handlers.wsgi.WSGIRequest
    @param request: Request
    @rtype: django.http.JsonResponse
    @return: JSON response (task state metadata)
    """
    data = {"success": False, "errmsg": "undefined"}
    try:
        if request.is_ajax():
            if 'task_id' in request.POST.keys() and request.POST['task_id']:
                task_id = request.POST['task_id']
                task = AsyncResult(task_id)
                if task.state == "SUCCESS":
                    aggr_log = ""
                    for log_item in task.result.task_logger.log:
                        aggr_log += log_item.decode('utf-8') + '\n'  # '\n'.join(task.result.task_logger.log)
                    aggr_err = '\n'.join(task.result.task_logger.err)
                    data = {"success": True, "result": task.result.task_status == 0, "warning": task.result.task_status == 2, "state": task.state, "log": aggr_log, "err": aggr_err}
                    # Update specific properties in database; The result is returned as a TaskResult object.
                    # Main properties are uuid (internal information package identifier) and task_status (state of the information package).
                    # Additional properties are returned by the dictionary additional_data.
                    if task.result.uuid and task.result.task_status >= 0:
                        ip = InformationPackage.objects.get(uuid=task.result.uuid)
                        ip.statusprocess = task.result.task_status
                        date_obj = dateparse.parse_datetime(task.result.ip_state_xml.get_lastchange())
                        ip.last_change = date_obj
                        if task.result.uuid and task.result.additional_data:
                            #make json out of additional_data to be written to db
                            additional_data_str = json.dumps(task.result.additional_data)
                            ip.additional_data = additional_data_str
                            if 'identifier' in task.result.additional_data.keys() and task.result.additional_data['identifier'] != '':
                                ip.identifier = task.result.additional_data['identifier']
                            if 'storage_loc' in task.result.additional_data.keys():
                                ip.storage_loc = task.result.additional_data['storage_loc']
                        if task.result.task_name:
                            try:
                                wf = WorkflowModules.objects.get(identifier=task.result.task_name)
                                ip.last_task = wf
                            except Exception, err:
                                data[err].append("Last task workflow module not found!")
                            if task.result.task_name == "IPClose" or task.result.task_name == "IPDelete":
                                ip.path = ""
                        ip.save()
                else:
                    data = {"success": True, "result": task.state, "state": task.state, "info": task.info}
            else:
                data = {"success": False, "errmsg": "No task_id in the request"}
        else:
            data = {"success": False, "errmsg": "Not ajax"}
    except Exception, err:
        data = {"success": False, "errmsg": err.message}
        tb = traceback.format_exc()
        logging.error(str(tb))

    return JsonResponse(data)

# @login_required
# @csrf_exempt
# def get_directory_json(request):
#     uuid = request.POST['uuid']
#     package_name = os.listdir('/var/data/earkweb/work/'+uuid+'/')[0]
#     return JsonResponse({ "data": path_to_dict('/var/data/earkweb/work/'+uuid+'/'+package_name) })

@login_required
@csrf_exempt
def execute_chain(request):
    """
    Execute selected task using selected information package as input. Task modules are registered in WorkflowModules.
    The identifier of a workflow module corresponds with the task's class name. The task is executed using celery's
    'apply_async' method.

    @type request: django.core.handlers.wsgi.WSGIRequest
    @param request: Request

    @rtype: django.http.JsonResponse
    @return: JSON response (task execution metadata)
    """
    data = {"success": False, "errmsg": "Unknown error"}
    try:
        selected_ip = request.POST['selected_ip']
        selected_actions = request.POST['selected_actions']
        if not (selected_ip and selected_actions):
            return JsonResponse({"success": False, "errmsg": "Missing input parameter!"})

        actions = selected_actions.split("+")
        print actions

        data = {"success": True, "id": "jobid", "msg": selected_actions}
        # Get module description of the task to be executed from the database
        ip = InformationPackage.objects.get(pk=selected_ip)



        try:
            action_classes = []
            task_chain = []
            for act in actions:
                wfm = WorkflowModules.objects.get(pk=act)
                taskClass = getattr(tasks, wfm.identifier)
                print "Executing task %s" % taskClass.name
                action_classes.append(taskClass)
                task_chain.append(taskClass().s())

            task_chain[0] = action_classes[0]().s(DefaultTaskContext(ip.uuid, ip.path, "", "", {}))

            job = chain(task_chain).apply_async()

            data = {"success": True, "id": job.id}



            # SIPResetType = getattr(tasks, "SIPtoAIPReset")
            # sipresettask = SIPResetType()
            # SIPDeliveryValidationType = getattr(tasks, "SIPDeliveryValidation")
            # sipdeliveryvalidationtask = SIPDeliveryValidationType()
            # job = chain(
            #     sipresettask.s(DefaultTaskContext(ip.uuid, ip.path, "", "")),
            #     sipdeliveryvalidationtask.s()
            # ).apply_async();
            # data = {"success": True, "id": job.id}


            # action_classes = []
            # for act in actions:
            #     wfm = WorkflowModules.objects.get(pk=act)
            #     taskClass = getattr(tasks, wfm.identifier)
            #     print "Executing task %s" % taskClass.name
            #     # additional input parameters for the task can be passed through using the 'additional_params' dictionary.
            #     additional_data = {'packagename': ip.packagename }
            #     if wfm.identifier == SIPPackaging.__name__:
            #         additional_data['packagename'] = ip.packagename
            #     if wfm.identifier == AIPPackaging.__name__ or wfm.identifier == LilyHDFSUpload.__name__:
            #         additional_data['identifier'] = ip.identifier
            #     if wfm.identifier == AIPStore.__name__:
            #         additional_data['identifier'] = ip.identifier
            #         additional_data['storage_dest'] = config_path_storage
            #         print "Storage destination %s" % addisuccesstional_data['storage_dest']
            #     if wfm.identifier == DIPAcquireAIPs.__name__ or wfm.identifier == DIPExtractAIPs.__name__:
            #         dip = DIP.objects.get(name=ip.packagename)
            #         selected_aips = {}
            #         for aip in dip.aips.all():
            #             selected_aips[aip.identifier] = aip.source
            #         additional_data['selected_aips'] = selected_aips
            #     if wfm.identifier == AIPPackageMetsCreation.__name__:
            #         additional_data['identifier'] = ip.identifier
            #
            #
            #
            #     mul.s.apply_async((10,), queue='default')
            #
            #
            #     (AIPPackaging(ip.uuid, ip.path, additional_data), DIPAcquireAIPs(ip.uuid, ip.path, additional_data)).apply_async(queue='default')
            #
            #     # Execute task
            #     job = taskClass().apply_async((ip.uuid, isuccessp.path, additional_data,), queue='default')
            #     data = {"success": True, "id": job.id}

        except Exception, err:
            tb = traceback.format_exc()
            print str(tb)
            return JsonResponse({"success": False, "errmsg": "Workflow module not found"})

#         # Get the selected information package from the database
#         ip = InformationPackage.objects.get(pk=selected_ip)
#         if request.is_ajax():
#             try:
#                 # Get task class from module identifier
#                 taskClass = getattr(tasks, wfm.identifier)
#                 print "Executing task %s" % taskClass.name
#                 # additional input parameters for the task can be passed through using the 'additional_params' dictionary.
#                 additional_data = {'packagename': ip.packagename }
#                 if wfm.identifier == SIPPackaging.__name__:
#                     additional_data['packagename'] = ip.packagename
#                 if wfm.identifier == AIPPackaging.__name__ or wfm.identifier == LilyHDFSUpload.__name__:
#                     additional_data['identifier'] = ip.identifier
#                 if wfm.identifier == AIPStore.__name__:
#                     additional_data['identifier'] = ip.identifier
#                     additional_data['storage_dest'] = config_path_storage
#                     print "Storage destination %s" % additional_data['storage_dest']
#                 if wfm.identifier == DIPAcquireAIPs.__name__ or wfm.identifier == DIPExtractAIPs.__name__:
#                     dip = DIP.objects.get(name=ip.packagename)
#                     selected_aips = {}
#                     for aip in dip.aips.all():
#                         selected_aips[aip.identifier] = aip.source
#                     additional_data['selected_aips'] = selected_aips
#                 if wfm.identifier == AIPPackageMetsCreation.__name__:
#                     additional_data['identifier'] = ip.identifier
#
#                 # Execute task
#                 job = taskClass().apply_async((ip.uuid, ip.path, additional_data,), queue='default')
#                 data = {"success": True, "id": job.id}
#             except AttributeError, err:
#                 errdetail = """The workflow module '%s' does not exist.
# It might be necessary to run 'python ./workers/scantasks.py' to register new or renamed tasks.""" % wfm.identifier
#                 data = {"success": False, "errmsg": "Workflow module '%s' does not exist" % wfm.identifier, "errdetail": errdetail}
#         else:
#             data = {"success": False, "errmsg": "not ajax"}
    except Exception, err:
        tb = traceback.format_exc()
        logging.error(str(tb))
        data = {"success": False, "errmsg": err.message, "errdetail": str(tb)}
        return JsonResponse(data)
    return JsonResponse(data)