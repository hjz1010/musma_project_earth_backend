import datetime
import calendar 

from django.http      import JsonResponse
from django.utils     import timezone
from django.views     import View
from django.db.models import Q

from core.utils       import PROGRESS_DETECTION
from core.emunutils   import DayEnum
from detection.models import Detection
from area.models      import Area


class RealTimeView(View):
    def get(self, request):
        try:
            detection_options = Detection.objects.filter(datetime__gte = timezone.now() - datetime.timedelta(seconds=10))
            real_time         = detection_options.first()

            if real_time == None :
                return JsonResponse({'message':'Not_Detected'}, status=400)
            
            results = [{
                'datetime'  : real_time.datetime,
                'type' : [{ 
                    'detection_info': detection_option.detection_type.name,
                    'state'         : detection_option.state.equipment_state,
                    } for detection_option in detection_options]
            }]
            
            return JsonResponse({'message':results}, status=200)

        except KeyError:
            JsonResponse({'message':'Key_Error'}, status=400)


class ProgressView(View):
    def get(self, request):
        try:
            select  = request.GET.get('select')
            area_id = request.GET.get('area')

            today = timezone.now().date()

            progress_detection = Detection.objects.filter(serial_number=PROGRESS_DETECTION)

            q = Q()
            if area_id:
                q &= Q(id=area_id)

            if select == 'realtime':
                results =[]
                for area in Area.objects.all():
                    results.append({
                        'name' : area.name,
                        'progress' : progress_detection.filter(area_id=area.id).last().progress\
                                        if progress_detection.filter(area_id=area.id) \
                                        else '없음'
                    })

            else:
                if select == 'weekly':
                    weekday     = today.isoweekday() # 1:월, 2:화, 3:수, 4:목, 5:금, 6:토, 7:일
                    last_sunday = today - datetime.timedelta(days=weekday)
                    dates       = [last_sunday + datetime.timedelta(days=Weekday.value) for Weekday in DayEnum]

                elif select == 'monthly':
                    last_date = calendar.monthrange(today.year,today.month)[1]
                    dates = [today.replace(day=date) for date in range(1, last_date+1)]
                else:
                    return JsonResponse({'message': 'Value_Error'}, status=404)
                
                areas = Area.objects.filter(q)
                if not areas:
                    return JsonResponse({'message': 'Value_Error'}, status=404)

                results = {}
                for area in areas:
                    progress_area =  progress_detection.filter(area=area)
                    start_date = progress_area.first().datetime.date() if progress_area else None
                    
                    results[area.name] = []
                    for date in dates:
                        if not start_date: 
                            progress = '없음'
                        else:     
                            progress_date_area = progress_area.filter(datetime__date=date)
                            if progress_date_area:
                                progress = progress_date_area.last().progress
                            elif start_date < date <= today :  
                                progress = progress_area.filter(datetime__date__lt=date).last().progress
                            elif date < start_date:  # date = start_date에는 progress_date_area.last().progress가 없을 수 없음
                                progress = 0
                            else: # today < date
                                progress = '없음'

                        results[area.name].append({
                            'day'     : date.day,
                            'progress': progress
                        })

            return JsonResponse({'message': 'SUCCESS', 'results': results}, status=200)

        except Exception as e:
            print('예외 발생:', e)
