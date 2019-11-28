from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from .models import Dept, Class, Student, Attendance, Course, Teacher, Assign, AttendanceTotal, time_slots, DAYS_OF_WEEK, AssignTime, AttendanceClass
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
import boto3
from boto3.dynamodb.conditions import Key, Attr
import datetime

import subprocess
# from face_recognition.create_database import create_database
# from face_recognition.record_face import record_face
# from face_recognition.training import  training
# from face_recognition.detector import detector
# Create your views here.

import time

@login_required
def index(request):
    if request.user.is_teacher:
        return render(request, 'AttedanceManager/t_homepage.html')
    if request.user.is_student:
        return render(request, 'AttedanceManager/homepage.html')
    return render(request, 'AttedanceManager/logout.html')


@login_required()
def attendance(request, stud_id):
    stud = Student.objects.get(USN=stud_id)
    ass_list = Assign.objects.filter(class_id_id=stud.class_id)
    att_list = []
    for ass in ass_list:
        try:
            a = AttendanceTotal.objects.get(student=stud, course=ass.course)
        except AttendanceTotal.DoesNotExist:
            a = AttendanceTotal(student=stud, course=ass.course)
            a.save()
        att_list.append(a)
    return render(request, 'AttedanceManager/attendance.html', {'att_list': att_list})


@login_required()
def attendance_detail(request, stud_id, course_id):
    stud = get_object_or_404(Student, USN=stud_id)
    cr = get_object_or_404(Course, id=course_id)
    att_list = Attendance.objects.filter(course=cr, student=stud).order_by('date')
    return render(request, 'AttedanceManager/att_detail.html', {'att_list': att_list, 'cr': cr})





# Teacher Views

@login_required
def t_clas(request, teacher_id, choice):
    teacher1 = get_object_or_404(Teacher, id=teacher_id)
    return render(request, 'AttedanceManager/t_clas.html', {'teacher1': teacher1, 'choice': choice})


@login_required()
def t_student(request, assign_id):
    ass = Assign.objects.get(id=assign_id)
    att_list = []
    for stud in ass.class_id.student_set.all():
        try:
            a = AttendanceTotal.objects.get(student=stud, course=ass.course)
        except AttendanceTotal.DoesNotExist:
            a = AttendanceTotal(student=stud, course=ass.course)
            a.save()
        att_list.append(a)
    return render(request, 'AttedanceManager/t_students.html', {'att_list': att_list})


@login_required()
def t_class_date(request, assign_id):
    now = timezone.now()
    ass = get_object_or_404(Assign, id=assign_id)
    att_list = ass.attendanceclass_set.filter(date__lte=now).order_by('-date')
    return render(request, 'AttedanceManager/t_class_date.html', {'att_list': att_list})




@login_required()
def t_attendance(request, ass_c_id):
    assc = get_object_or_404(AttendanceClass, id=ass_c_id)
    ass = assc.assign
    c = ass.class_id
    context = {
        'ass': ass,
        'c': c,
        'assc': assc,
    }
    return render(request, 'AttedanceManager/t_attendance.html', context)
#################


@login_required()
def edit_att(request, ass_c_id):
    assc = get_object_or_404(AttendanceClass, id=ass_c_id)
    cr = assc.assign.course
    att_list = Attendance.objects.filter(attendanceclass=assc, course=cr)
    context = {
        'assc': assc,
        'att_list': att_list,
    }
    return render(request, 'AttedanceManager/t_edit_att.html', context)

@login_required()
def takeattendance(request,ass_c_id):
    assc = get_object_or_404(AttendanceClass, id=ass_c_id)
    ass = assc.assign
    cr = ass.course
    cl = ass.class_id
    assign_id=ass.id

    ass = Assign.objects.get(id=assign_id)
    att_list = []
    for stud in ass.class_id.student_set.all():
        try:
            a = AttendanceTotal.objects.get(student=stud, course=ass.course)
        except AttendanceTotal.DoesNotExist:
            a = AttendanceTotal(student=stud, course=ass.course)
            a.save()
        att_list.append(a)


    # connection server dynamo db.
    db = boto3.resource('dynamodb')
    #teacher_table = db.Table("rfid_details")
    #x = "abc"
    #response = teacher_table.scan(FilterExpression=Attr('tname').eq(x))
    # t_rfid = response['Items'][0]["teacher_id"]

    # get rfid from django server
    t_rfid=ass.teacher.rfid
    print(t_rfid)


    student_table = db.Table("student_attendance")
    response = student_table.scan(FilterExpression=Attr('teacher_id').eq(t_rfid))
    all_student = response["Items"]
    student_usn_list = []
    for i in all_student:
        student_usn_list.append(i["usn"])
    not_in_class=[]
    x=[s.USN for s in cl.student_set.all()]
    for i in student_usn_list :
        if i not in x:
            not_in_class.append(i)
    print("list sent from server",student_usn_list)
    print("students in your class",x)
    print("Members illegally attending your class",not_in_class)


    print(student_usn_list)
    for i, s in enumerate(cl.student_set.all()):
        # status = request.POST[s.USN]     #mereko ye post object chahiye which we are gettin
        # if status == 'present':
        #     status = 'True'
        # else:
        #     status = 'False'
        status='False'
        if s.USN in student_usn_list:
            status='True'
        if assc.status == 1:
            try:
                a = Attendance.objects.get(course=cr, student=s, date=assc.date, attendanceclass=assc)
                a.status = status
                a.save()
            except Attendance.DoesNotExist:
                a = Attendance(course=cr, student=s, status=status, date=assc.date, attendanceclass=assc)
                a.save()
        else:
            a = Attendance(course=cr, student=s, status=status, date=assc.date, attendanceclass=assc)
            a.save()
            assc.status = 1
            assc.save()
    #return render(request, 'AttedanceManager/t_class_date.html', {'att_list': att_list})
    return render(request, 'AttedanceManager/t_classattendacnce.html')




@login_required()
def confirm(request, ass_c_id):
    #connect to dynamodb and  retrieve tabele AttedanceManagerrmation
    #tell dynamodb database to send this AttedanceManagerrmation in the form of post response.

    assc = get_object_or_404(AttendanceClass, id=ass_c_id)
    ass = assc.assign
    cr = ass.course
    cl = ass.class_id

    db = boto3.resource('dynamodb')
    teacher_table = db.Table("rfid_details")
    x = "abc"
    response = teacher_table.scan(FilterExpression=Attr('tname').eq(x))
    t_rfid = response['Items'][0]["teacher_id"]
    t_rfid = int(t_rfid)

    student_table = db.Table("student_attendance")
    response = student_table.scan(FilterExpression=Attr('teacher_id').eq(t_rfid))
    all_student = response["Items"]
    student_usn_list = []
    for i in all_student:
        student_usn_list.append(i["usn"])

    for i, s in enumerate(cl.student_set.all()):
        # status = request.POST[s.USN]     #mereko ye post object chahiye which we are gettin
        # if status == 'present':
        #     status = 'True'
        # else:
        #     status = 'False'
        if s.USN in student_usn_list:
            status='True'
        if assc.status == 1:
            try:
                a = Attendance.objects.get(course=cr, student=s, date=assc.date, attendanceclass=assc)
                a.status = status
                a.save()
            except Attendance.DoesNotExist:
                a = Attendance(course=cr, student=s, status=status, date=assc.date, attendanceclass=assc)
                a.save()
        else:
            a = Attendance(course=cr, student=s, status=status, date=assc.date, attendanceclass=assc)
            a.save()
            assc.status = 1
            assc.save()

    return HttpResponseRedirect(reverse('t_class_date', args=(ass.id,)))

# def viewattendance(request):
#     stud = get_object_or_404(Student, USN=stud_id)
#     cr = get_object_or_404(Course, id=course_id)
#     att_list = Attendance.objects.filter(course=cr, student=stud).order_by('date')
#
#     return (render(request,'AttedanceManager/t_classattendacnce.html',{}))

@login_required()
def t_attendance_detail(request, stud_id, course_id):
    stud = get_object_or_404(Student, USN=stud_id)
    cr = get_object_or_404(Course, id=course_id)
    att_list = Attendance.objects.filter(course=cr, student=stud).order_by('date')
    return render(request, 'AttedanceManager/t_att_detail.html', {'att_list': att_list, 'cr': cr})

