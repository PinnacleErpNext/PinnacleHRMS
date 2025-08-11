import frappe
import json
import calendar
from datetime import datetime, time, timedelta, date
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from pprint import pprint


def createPaySlips(data):

    year = int(data.get("year"))
    month = data.get("month")

    empRecords = getEmpRecords(data)

    employeeData = calculateMonthlySalary(empRecords, year, month)

    # return frappe.throw(str(dict(employeeData)))

    total_employees = len(employeeData)
    progress = 0

    for index, (emp_id, data) in enumerate(employeeData.items(), start=1):
        progress = int((index / total_employees) * 100)
        frappe.publish_progress(
            progress,
            title="Creating Pay Slips",
            description=f"Creating Pay Slip for {emp_id}",
        )
        if frappe.db.exists(
            "Pay Slips",
            {"employee_id": data.get("employee"), "month_num": month, "year": year},
        ):
            continue
        else:
            salaryInfo = data.get("salary_information", {})

            # Calculations
            fullDayWorkingAmount = round(
                (salaryInfo.get("full_days", 0) * salaryInfo.get("per_day_salary", 0)),
                2,
            )
            earlyCheckoutWorkingAmount = round(
                (
                    salaryInfo.get("early_checkout_days", 0)
                    * salaryInfo.get("per_day_salary", 0)
                ),
                2,
            )
            quarterDayWorkingAmount = round(
                (
                    salaryInfo.get("quarter_days", 0)
                    * salaryInfo.get("per_day_salary", 0)
                    * 0.25
                ),
                2,
            )
            halfDayWorkingAmount = round(
                (
                    salaryInfo.get("half_days", 0)
                    * 0.5
                    * salaryInfo.get("per_day_salary", 0)
                ),
                2,
            )
            threeFourQuarterDaysWorkingAmount = round(
                (
                    salaryInfo.get("three_four_quarter_days", 0)
                    * 0.75
                    * salaryInfo.get("per_day_salary", 0)
                ),
                2,
            )
            latesAmount = round(
                (
                    salaryInfo.get("lates", 0)
                    * salaryInfo.get("per_day_salary", 0)
                    * 0.9
                ),
                2,
            )
            othersDayAmount = salaryInfo.get("others_day_salary")
            # print(othersDayAmount)
            otherEarningsAmount = round(
                (salaryInfo.get("overtime", 0)), 2
            ) + salaryInfo.get("leave_encashment")

            monthMapping = {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July",
                8: "August",
                9: "September",
                10: "October",
                11: "November",
                12: "December",
            }
            monthName = monthMapping.get(month)

            # Create a new Pay Slip document
            paySlip = frappe.get_doc(
                {
                    "doctype": "Pay Slips",
                    "docstatus": 0,
                    "year": year,
                    "month": monthName,
                    "month_num": month,
                    "company": data.get("company"),
                    "employee": data.get("employee"),
                    "employee_name": data.get("employee_name"),
                    "email": data.get("email"),
                    "designation": data.get("designation"),
                    "department": data.get("department"),
                    "pan_number": data.get("pan_number"),
                    "date_of_joining": data.get("date_of_joining"),
                    "attendance_device_id": data.get("attendance_device_id"),
                    "basic_salary": data.get("basic_salary"),
                    "per_day_salary": salaryInfo.get("per_day_salary"),
                    "standard_working_days": salaryInfo.get("standard_working_days"),
                    "others_days": salaryInfo.get("others_day"),
                    "absent": salaryInfo.get("absent"),
                    "actual_working_days": salaryInfo.get("actual_working_days"),
                    "net_payble_amount": salaryInfo.get("total_salary"),
                    "other_earnings_amount": otherEarningsAmount,
                    "total": round(
                        (
                            fullDayWorkingAmount
                            + quarterDayWorkingAmount
                            + halfDayWorkingAmount
                            + threeFourQuarterDaysWorkingAmount
                            + latesAmount
                            + salaryInfo.get("sundays_salary")
                            + earlyCheckoutWorkingAmount
                            + othersDayAmount
                        ),
                        2,
                    ),
                }
            )

            if salaryInfo.get("full_days"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Full Day",
                        "days": salaryInfo.get("full_days"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "100",
                        "amount": fullDayWorkingAmount,
                    },
                )
            if salaryInfo.get("lates"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Lates",
                        "days": salaryInfo.get("lates"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "90",
                        "amount": latesAmount,
                    },
                )
            if salaryInfo.get("three_four_quarter_days"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "3/4 Quarter Day",
                        "days": salaryInfo.get("three_four_quarter_days"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "75",
                        "amount": threeFourQuarterDaysWorkingAmount,
                    },
                )
            if salaryInfo.get("half_days"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Half Day",
                        "days": salaryInfo.get("half_days"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "50",
                        "amount": halfDayWorkingAmount,
                    },
                )
            if salaryInfo.get("quarter_days"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Quarter Day",
                        "days": salaryInfo.get("quarter_days"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "25",
                        "amount": quarterDayWorkingAmount,
                    },
                )
            if salaryInfo.get("others_day"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Others Day",
                        "days": salaryInfo.get("others_day"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "-",
                        "amount": othersDayAmount,
                    },
                )
            if salaryInfo.get("sundays_working_days"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Sunday Workings",
                        "days": salaryInfo.get("sundays_working_days"),
                        "rate": salaryInfo.get("per_day_salary"),
                        "effective_percentage": "100",
                        "amount": salaryInfo.get("sundays_salary"),
                    },
                )
            paySlip.append(
                "other_earnings",
                {
                    "type": "Incentives",
                    "amount": 0,
                },
            )
            paySlip.append(
                "other_earnings",
                {
                    "type": "Special Incentives",
                    "amount": 0,
                },
            )
            paySlip.append(
                "other_earnings",
                {
                    "type": "Leave Encashment",
                    "amount": salaryInfo.get("leave_encashment"),
                },
            )
            paySlip.append(
                "other_earnings",
                {
                    "type": "Overtime",
                    "amount": salaryInfo.get("overtime"),
                },
            )
            # paySlip.append(
            #     "other_earnings",
            #     {
            #         "type": "Holidays",
            #         "amount": salaryInfo.get("holidays"),
            #     },
            # )

            attendanceRecord = frappe.render_template(
                "pinnaclehrms/public/templates/attendance_record.html",
                {"attendance_record": data.get("attendance_records")},
            )
            paySlip.attendance_record = attendanceRecord

            # Insert the new document to save it in the database
            paySlip.insert()

            encashment = getEncashment(emp_id, year, month)

            if encashment:
                encashment_name = encashment[0].name
                encashment_amount = encashment[0].amount

                frappe.db.set_value(
                    "Pinnacle Leave Encashment",
                    encashment_name,
                    {
                        "status": "Paid",
                        "pay_slip": paySlip.name,
                    },
                )


def getEmpRecords(data):

    # Construct the base query
    baseQuery = """
            SELECT
                e.company,
                e.employee,
                e.employee_name,
                e.company_email as email,
                e.designation,
                e.department,
                e.pan_number,
                e.date_of_joining,
                e.relieving_date,
                e.attendance_device_id,
                e.default_shift,
                e.holiday_list,
                a.attendance_date,
                a.in_time,
                a.out_time
            FROM
                tabEmployee e
            JOIN
                tabAttendance a ON e.employee = a.employee
            WHERE
                e.status in ("Active","Left")  AND a.docstatus = 1 AND YEAR(a.attendance_date) = %s AND MONTH(a.attendance_date) = %s
        """

    year = int(data.get("year"))
    month = int(data.get("month"))

    if not year or not month:
        return frappe.throw("Select year and month")

    filters = [year, month]

    autoCalculateLeaveEncashment = data.get("auto_calculate_leave_encashment")
    lates = data.get("allowed_lates")

    # Check for company or employee selection

    if data.get("select_company"):
        company = data.get("select_company")
        baseQuery += "AND e.company = %s"
        filters.append(company)
    if data.get("employee_list"):
        employee = data.get("employee_list")
        baseQuery += "AND e.employee in %s"
        filters.append(employee)
    if data.get("select_employee"):
        employee = data.get("select_employee")
        baseQuery += "AND e.employee = %s"
        filters.append(employee)

    date = f"{year}-{month:02d}-01"

    records = frappe.db.sql(baseQuery, filters, as_dict=False)

    # records = get_employee_attendance(data)
    # frappe.throw(str(records))
    if not records:
        return frappe.throw("No records found!")

    # Initialize a defaultdict to organize employee records
    empRecords = defaultdict(
        lambda: {
            "company": "",
            "employee": "",
            "employee_name": "",
            "email": "",
            "designation": "",
            "department": "",
            "pan_number": "",
            "date_of_joining": "",
            "relieving_date": "",
            "auto_calculate_leave_encashment": "",
            "lates": "",
            "holidays": "",
            "working_days": "",
            "holiday_list": "",
            "basic_salary": 0,
            "attendance_device_id": "",
            "attendance_records": [],
            "salary_information": {},
        }
    )

    # Populate employee records from the query results
    for record in records:
        (
            company,
            employee_id,
            employee_name,
            email,
            designation,
            department,
            pan_number,
            date_of_joining,
            relieving_date,
            attendance_device_id,
            shift,
            holiday_list,
            attendance_date,
            in_time,
            out_time,
        ) = record
        salaryDetails = getSalaryDetails(employee_id, year, month)

        if salaryDetails:
            basicSalary = salaryDetails.get("basicSalary")
            isOvertime = salaryDetails.get("overtimeEligibility")
        else:
            frappe.throw("No salary detail found!")

        holidays = frappe.db.sql(
            """
                                SELECT holiday_date FROM tabHoliday 
                                WHERE MONTH(holiday_date) = %s AND YEAR(holiday_date) = %s AND parent = %s """,
            (month, year, holiday_list),
            as_dict=True,
        )

        if empRecords[employee_id]["employee"]:
            # Employee already exists, append to attendance_records
            empRecords[employee_id]["attendance_records"].append(
                {
                    "attendance_date": attendance_date,
                    "shift": shift,
                    "in_time": in_time,
                    "out_time": out_time,
                }
            )
        else:
            # Add new employee data
            empRecords[employee_id] = {
                "company": company,
                "employee": employee_id,
                "employee_name": employee_name,
                "email": email,
                "designation": designation,
                "department": department,
                "pan_number": pan_number,
                "date_of_joining": date_of_joining,
                "relieving_date": relieving_date,
                "auto_calculate_leave_encashment": autoCalculateLeaveEncashment,
                "lates": lates,
                "holidays": holidays,
                "total_working_days": calendar.monthrange(year, month)[1],
                "basic_salary": basicSalary,
                "is_overtime": isOvertime,
                "attendance_device_id": attendance_device_id,
                "shift": shift,
                "holiday_list": holiday_list,
                "attendance_records": [
                    {
                        "attendance_date": attendance_date,
                        "shift": shift,
                        "in_time": in_time,
                        "out_time": out_time,
                    }
                ],
                "salary_information": {},
            }

    # Calculate monthly salary for each employe
    # frappe.throw(str(dict(empRecords)))

    return empRecords


def calculateShiftTimes(attendanceDate, shiftStart, shiftEnd):
    # Extract hours and minutes from shift start and end
    if isinstance(shiftStart, datetime) or isinstance(shiftEnd, datetime):
        # Convert to time object
        if isinstance(shiftStart, datetime):
            shiftStart = shiftStart.time()
        if isinstance(shiftEnd, datetime):
            shiftEnd = shiftEnd.time()

        # Now convert time to timedelta
        shiftStart = timedelta(
            hours=shiftStart.hour, minutes=shiftStart.minute, seconds=shiftStart.second
        )
        shiftEnd = timedelta(
            hours=shiftEnd.hour, minutes=shiftEnd.minute, seconds=shiftEnd.second
        )
    startHours, remainder = divmod(shiftStart.seconds, 3600)
    startMinutes, _ = divmod(remainder, 60)
    endHours, remainder = divmod(shiftEnd.seconds, 3600)
    endMinutes, _ = divmod(remainder, 60)

    # Calculate ideal check-in/out times
    idealCheckInTime = datetime.combine(attendanceDate, time(startHours, startMinutes))
    idealCheckOutTime = datetime.combine(attendanceDate, time(endHours, endMinutes))

    # Define overtime threshold (example: 7:30 PM)
    overtimeThreshold = datetime.combine(attendanceDate, time(19, 30))

    # Calculate ideal working hours
    idealWorkingTime = idealCheckOutTime - idealCheckInTime
    idealWorkingHours = idealWorkingTime.total_seconds() / 3600

    return {
        "idealCheckInTime": idealCheckInTime,
        "idealCheckOutTime": idealCheckOutTime,
        "overtimeThreshold": overtimeThreshold,
        "idealWorkingHours": idealWorkingHours,
    }


def createTimeSlabs(check_in_time, check_out_time):
    ideal_working_time = check_out_time - check_in_time
    iwh = ideal_working_time.total_seconds() / 60

    slabs = {
        "check_in": [
            (
                check_in_time,
                check_in_time + timedelta(minutes=round(iwh * 0.112)),
                0.10,
            ),  # 10% deduction
            (
                check_in_time + timedelta(minutes=round(iwh * 0.112)),
                check_in_time + timedelta(minutes=round(iwh * 0.334)),
                0.25,
            ),  # 25% deduction
            (
                check_in_time + timedelta(minutes=round(iwh * 0.334)),
                check_in_time + timedelta(minutes=round(iwh * 0.667)),
                0.50,
            ),  # 50% deduction
            (
                check_in_time + timedelta(minutes=round(iwh * 0.667)),
                check_in_time + timedelta(minutes=round(iwh * 1)),
                0.75,
            ),  # 75% deduction
        ],
        "check_out": [
            (
                check_out_time - timedelta(minutes=round(iwh * 1)),
                check_out_time - timedelta(minutes=round(iwh * 0.664)),
                0.75,
            ),  # 75% deduction
            (
                check_out_time - timedelta(minutes=round(iwh * 0.664)),
                check_out_time - timedelta(minutes=round((iwh * 0.331))),
                0.50,
            ),  # 50% deduction
            (
                check_out_time - timedelta(minutes=round((iwh * 0.331))),
                check_out_time - timedelta(minutes=round((iwh * 0.109))),
                0.25,
            ),  # 25% deduction
            (
                check_out_time - timedelta(minutes=round((iwh * 0.109))),
                check_out_time,
                0.10,
            ),  # 10% deduction
        ],
    }
    return slabs


def calculateDeduction(checkIn, checkOut, slabs):
    deductionPercentage = 0.0

    # Check which check-in slab applies
    for start, end, rate in slabs["check_in"]:
        if start < checkIn <= end:
            deductionPercentage += rate
            break

    # Check which check-out slab applies
    for start, end, rate in slabs["check_out"]:
        if start <= checkOut < end:
            deductionPercentage += rate
            break

    return deductionPercentage


def calculateFinalAmount(perDaySalary, deductionPercentage):

    return perDaySalary * (1 - deductionPercentage)


def calculateMonthlySalary(employeeData, year, month):

    month = int(month)
    year = int(year)

    if month >= 4:
        # Financial year starts in the current year and ends in the next year
        startYear = year
        endYear = year + 1
    else:
        # Financial year starts in the previous year and ends in the current year
        startYear = year - 1
        endYear = year

    # Define start and end dates of the financial year
    startDate = datetime(startYear, 4, 1)
    endDate = datetime(endYear, 3, 31)

    for emp_id, data in employeeData.items():
        totalSalary = 0.0
        totalLateDeductions = 0.0
        fullDays = 0
        halfDays = 0
        quarterDays = 0
        threeFourQuarterDays = 0
        totalAbsents = 0
        lates = 0
        sundays = 0
        othersDay = 0
        othersDaySalary = 0
        sundaysSalary = 0.0
        overtimeSalary = 0.0
        actualWorkingDays = 0
        leaveEncashmentAmount = 0
        earlyCheckOutDays = 0
        holidayAmount = 0
        empAttendance = {
            "date": None,
            "deductionPercentage": None,
            "salary": None,
            "status": None,
        }
        empAttendanceRecord = []

        basicSalary = data.get("basic_salary", 0)
        attendanceRecords = data.get("attendance_records", [])
        isOvertime = data.get("is_overtime")
        autoCalculateLeaveEncashment = data.get("auto_calculate_leave_encashment")
        allowedLates = data.get("lates")
        holidays = data.get("holidays")
        totalWorkingDays = data.get("total_working_days")
        company = frappe.db.get_value("Employee", emp_id, "company")

        shiftVariationRecord = frappe.db.sql(
            """SELECT 
                    sv.shift_date AS attendance_date, 
                    sv.name AS shift_variation_names,  
                    GROUP_CONCAT(DISTINCT sfe.employee) AS employees, 
                    sv.shift_start AS earliest_in_time, 
                    sv.shift_end AS latest_out_time 
                FROM 
                    `tabShift Variation` AS sv 
                LEFT JOIN 
                    `tabShift for employee` AS sfe ON sv.name = sfe.parent 
                WHERE 
                    YEAR(sv.shift_date) = %s 
                    AND MONTH(sv.shift_date) = %s 
                    AND sv.company = %s
                GROUP BY 
                    sv.shift_date;
            """,
            (year, month, company),
            as_dict=True,
        )

        dojStr = data.get("date_of_joining")
        doj = (
            datetime.strptime(dojStr, "%Y-%m-%d") if isinstance(dojStr, str) else dojStr
        )

        currentDate = datetime.today().date()
        workingPeriod = (relativedelta(currentDate, doj)).years
        leaveEncashmentData = getEncashment(emp_id, year, month)
        
        if len(leaveEncashmentData) > 0:
            leaveEncashmentAmount = leaveEncashmentData[0].get("amount",0)

        if doj.month == month:
            filterdHolidays = []
            for day in holidays:
                if day.get("holiday_date") >= doj:
                    filterdHolidays.append({"holiday_date": day.get("holiday_date")})
            holidays = filterdHolidays

        if data.get("relieving_date"):

            filterdHolidays = []
            for day in holidays:
                if day.get("holiday_date") <= data.get("relieving_date"):
                    filterdHolidays.append({"holiday_date": day.get("holiday_date")})

            holidays = filterdHolidays

        # frappe.throw(str(holidays))
        perDaySalary = round(basicSalary / totalWorkingDays, 2)
        holidayAmount = perDaySalary * len(holidays)

        # for holidayDate in holidays:
        #     holiday = holidayDate["holiday_date"]

        #     dayBeforeHoliday = holiday - timedelta(days=1)
        #     dayAfterHoliday = holiday + timedelta(days=1)

        #     # Check if attendance exists before and after the holiday
        #     attendanceBefore = any(
        #         attendanceRecord["attendance_date"] == dayBeforeHoliday for attendanceRecord in attendanceRecords
        #     )
        #     attendanceAfter = any(
        #         attendanceRecord["attendance_date"] == dayAfterHoliday for attendanceRecord in attendanceRecords
        #     )

        #     # Check if the days before and after are also holidays
        #     isHolidayBefore = any(
        #         h["holiday_date"] == dayBeforeHoliday for h in holidays
        #     )
        #     isHolidayAfter = any(
        #         h["holiday_date"] == dayAfterHoliday for h in holidays
        #     )

        #     # Credit holiday amount if conditions are met
        #     if attendanceBefore or attendanceAfter or (isHolidayBefore and isHolidayAfter):
        #         holidayAmount += perDaySalary
        #         print(holidayDate)
        #         print(holidayAmount)

        for day in range(1, totalWorkingDays + 1):
            today = datetime(year, month, day).date()

            attendanceRecord = next(
                (
                    record
                    for record in attendanceRecords
                    if record["attendance_date"] == today
                ),
                None,
            )

            attendanceDate = today
            salary = 0

            perDaySalary = round(basicSalary / totalWorkingDays, 2)

            if attendanceRecord:
                attendanceDate = attendanceRecord["attendance_date"]
                inTime = attendanceRecord["in_time"]
                outTime = attendanceRecord["out_time"]

                shiftDetails = getShiftDetails(attendanceDate, attendanceRecord)

                idealCheckInTime = shiftDetails.get("idealCheckInTime")
                idealCheckOutTime = shiftDetails.get("idealCheckOutTime")
                overtimeThreshold = shiftDetails.get("overtimeThreshold")

                if (
                    inTime
                    and outTime
                    and (inTime != "00:00:00" and outTime != "00:00:00")
                    and (outTime > inTime)
                ):

                    actCheckIn = inTime
                    actCheckOut = outTime
                    attendance = getAttendance(
                        emp_id,
                        shiftVariationRecord,
                        attendanceDate,
                        attendanceRecord,
                        shiftDetails,
                    )

                    inTime = attendance.get("in_time")
                    outTime = attendance.get("out_time")

                    checkIn = datetime.combine(attendanceDate, inTime.time())
                    checkOut = datetime.combine(attendanceDate, outTime.time())
                    status = ""

                    totalWorkingTime = checkOut - checkIn
                    totalWorkingHours = round(
                        (totalWorkingTime.total_seconds() / 3600), 2
                    )

                    slabs = createTimeSlabs(idealCheckInTime, idealCheckOutTime)
                    if totalWorkingHours > 3:

                        deductionPercentage = calculateDeduction(
                            checkIn, checkOut, slabs
                        )
                        salary = calculateFinalAmount(
                            perDaySalary, deductionPercentage
                        )  # call getBasicSaly inside this

                        # if checkIn > idealCheckInTime and (
                        #     deductionPercentage == 0.1 or deductionPercentage == 0.2
                        # ):
                        #     if lates < allowedLates:
                        #         totalSalary += perDaySalary * 0.1

                        # overtime salary calculation if marked is eligible
                        if isOvertime and checkOut > overtimeThreshold:
                            extraTime = checkOut - idealCheckOutTime
                            overtime = extraTime.total_seconds() / 60
                            minOvertimeSalary = perDaySalary / 540
                            overtimeSalary = overtime * minOvertimeSalary

                        if deductionPercentage == 0:
                            if attendanceDate.weekday() == 6:
                                sundays += 1
                                actualWorkingDays += 1
                                status = "Sunday"
                                sundaysSalary += salary
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                            else:
                                fullDays += 1
                                actualWorkingDays += 1
                                status = "Full Day"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                                totalSalary += salary
                        elif deductionPercentage == 0.1:
                            if attendanceDate.weekday() == 6:
                                sundays += 1
                                actualWorkingDays += 1
                                status = "Sunday"
                                sundaysSalary += salary
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                            else:
                                if allowedLates == 0:
                                    lates += 1
                                    actualWorkingDays += 1
                                    status = "Late"
                                    empAttendanceRecord.append(
                                        {
                                            "date": attendanceDate,
                                            "deductionPercentage": deductionPercentage,
                                            "salary": round(salary, 2),
                                            "status": status,
                                            "check_in": actCheckIn.time(),
                                            "check_out": actCheckOut.time(),
                                        }
                                    )
                                    totalSalary += salary
                                elif (
                                    checkOut < idealCheckOutTime
                                    and (
                                        checkIn < idealCheckInTime
                                        or checkIn == idealCheckInTime
                                    )
                                    and allowedLates == 0
                                ):
                                    actualWorkingDays += 1
                                    lates += 1
                                    status = "Early Check Out"
                                    empAttendanceRecord.append(
                                        {
                                            "date": attendanceDate,
                                            "deductionPercentage": deductionPercentage,
                                            "salary": round(salary, 2),
                                            "status": status,
                                            "check_in": actCheckIn.time(),
                                            "check_out": actCheckOut.time(),
                                        }
                                    )
                                    totalSalary += salary
                                else:
                                    allowedLates -= 1

                                    totalSalary += round(perDaySalary, 2)
                                    actualWorkingDays += 1
                                    fullDays += 1
                                    status = "Full Day"
                                    empAttendanceRecord.append(
                                        {
                                            "date": attendanceDate,
                                            "deductionPercentage": 0.0,
                                            "salary": round(perDaySalary, 2),
                                            "status": status,
                                            "check_in": actCheckIn.time(),
                                            "check_out": actCheckOut.time(),
                                        }
                                    )
                        elif deductionPercentage == 0.25:
                            if attendanceDate.weekday() == 6:
                                sundays += 1
                                actualWorkingDays += 1
                                status = "Sunday"
                                sundaysSalary += salary
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                            else:
                                threeFourQuarterDays += 1
                                actualWorkingDays += 1
                                status = "3/4"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                                totalSalary += salary
                        elif deductionPercentage == 0.5:
                            if attendanceDate.weekday() == 6:
                                sundays += 1
                                actualWorkingDays += 1
                                status = "Sunday"
                                sundaysSalary += salary
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                            else:
                                halfDays += 1
                                actualWorkingDays += 1
                                status = "Half Day"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                                totalSalary += salary
                        elif deductionPercentage == 0.25:
                            if attendanceDate.weekday() == 6:
                                sundays += 1
                                actualWorkingDays += 1
                                status = "Sunday"
                                sundaysSalary += salary
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                            else:
                                quarterDays += 1
                                actualWorkingDays += 1
                                status = "Quarter"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                                totalSalary += salary
                        else:
                            if attendanceDate.weekday() == 6:
                                sundays += 1
                                actualWorkingDays += 1
                                status = "Sunday"
                                sundaysSalary += salary
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                            else:
                                othersDay += 1
                                actualWorkingDays += 1
                                status = "Others"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": round(salary, 2),
                                        "status": status,
                                        "check_in": actCheckIn.time(),
                                        "check_out": actCheckOut.time(),
                                    }
                                )
                                othersDaySalary += salary
                    else:
                        deductionPercentage = 1
                        if any(
                            holiday["holiday_date"] == today for holiday in holidays
                        ):
                            pass
                        else:
                            totalAbsents += 1
                            status = "Absent"
                            empAttendanceRecord.append(
                                {
                                    "date": attendanceDate,
                                    "deductionPercentage": 1,
                                    "salary": round(salary, 2),
                                    "status": status,
                                    "check_in": actCheckIn.time(),
                                    "check_out": actCheckOut.time(),
                                }
                            )
                    # print(today, deductionPercentage, salary, status,totalSalary)
                else:
                    if any(holiday["holiday_date"] == today for holiday in holidays):
                        pass
                    else:
                        if inTime:
                            inTime = inTime.time()
                        if outTime:
                            outTime = outTime.time()
                        totalAbsents += 1
                        status = "Absent"
                        empAttendanceRecord.append(
                            {
                                "date": attendanceDate,
                                "deductionPercentage": 1,
                                "salary": round(salary, 2),
                                "status": status,
                                "check_in": inTime,
                                "check_out": outTime,
                            }
                        )
            else:
                if any(holiday["holiday_date"] == today for holiday in holidays):
                    pass
                else:
                    checkIn = time(0, 0, 0)
                    checkOut = time(0, 0, 0)
                    totalAbsents += 1
                    status = "Absent"
                    empAttendanceRecord.append(
                        {
                            "date": attendanceDate,
                            "deductionPercentage": 1,
                            "salary": round(salary, 2),
                            "status": status,
                            "check_in": checkIn,
                            "check_out": checkOut,
                        }
                    )

        if actualWorkingDays > 0:
            totalSalary += (
                overtimeSalary + holidayAmount + leaveEncashmentAmount + sundaysSalary + othersDaySalary
            )
            pass
        else:
            holidayAmount = 0
            totalSalary += overtimeSalary + leaveEncashmentAmount

        data["attendance_records"] = empAttendanceRecord

        data["salary_information"] = {
            "basic_salary": basicSalary,
            "per_day_salary": perDaySalary,
            "standard_working_days": totalWorkingDays,
            "actual_working_days": actualWorkingDays,
            "full_days": fullDays + len(holidays),
            "half_days": halfDays,
            "quarter_days": quarterDays,
            "three_four_quarter_days": threeFourQuarterDays,
            "sundays_working_days": sundays,
            "early_checkout_days": earlyCheckOutDays,
            "others_day": othersDay,
            "others_day_salary":othersDaySalary,
            "sundays_salary": sundaysSalary,
            "total_salary": round(totalSalary, 2),
            "total_late_deductions": totalLateDeductions,
            "absent": totalAbsents,
            "lates": lates,
            "overtime": round((overtimeSalary), 2),
            "holidays": holidayAmount,
            "leave_encashment": round((leaveEncashmentAmount), 2),
        }

    return employeeData


def getSalaryDetails(emp_id, year, month):
    # Initialize default salary details
    salaryDetails = {"basicSalary": 0.0, "overtimeEligibility": 1}

    # Query salary records for the specific month and year
    salaryIncrement = frappe.db.sql(
        """
        SELECT 
            tsh.from_date,
            tsh.salary,
            tas.eligible_for_overtime_salary
        FROM 
            `tabSalary History` AS tsh
        JOIN 
            `tabAssign Salary` AS tas
        ON 
            tsh.parent = tas.name
        WHERE 
            tas.employee_id = %s
            AND YEAR(tsh.from_date) = %s
            AND MONTH(tsh.from_date) = %s;
    """,
        (emp_id, year, month),
        as_dict=True,
    )

    if salaryIncrement:
        incrementDate = salaryIncrement[0].from_date
        # If the increment is effective from the first day, use this record directly
        if incrementDate.day == 1:
            basicSalary = salaryIncrement[0].salary
            overtimeEligibility = salaryIncrement[0].eligible_for_overtime_salary
        else:
            # Calculate weighted salary if increment is not on the 1st
            totalWorkingDays = calendar.monthrange(year, month)[1]
            # Ensure month-1 is valid; add rollover logic if month == 1
            previousMonth = month - 1 if month > 1 else 12
            previousYear = year if month > 1 else year - 1
            salaryData = frappe.db.sql(
                """
                SELECT 
                    tsh.salary
                FROM 
                    `tabSalary History` AS tsh
                JOIN 
                    `tabAssign Salary` AS tas
                ON 
                    tsh.parent = tas.name
                WHERE 
                    tas.employee_id = %s
                    AND (YEAR(tsh.from_date) < %s 
                         OR (YEAR(tsh.from_date) = %s AND MONTH(tsh.from_date) <= %s))
                ORDER BY 
                    tsh.from_date DESC
                LIMIT 1;
            """,
                (emp_id, year, previousYear, previousMonth),
                as_dict=True,
            )

            if salaryData:
                beforeIncrementSalary = (incrementDate.day - 1) * (
                    salaryData[0].salary / totalWorkingDays
                )
                afterIncrementSalary = ((totalWorkingDays - incrementDate.day) + 1) * (
                    salaryIncrement[0].salary / totalWorkingDays
                )
                basicSalary = beforeIncrementSalary + afterIncrementSalary
                overtimeEligibility = salaryIncrement[0].eligible_for_overtime_salary
            else:
                # Fallback if no previous data found
                basicSalary = salaryIncrement[0].salary
                overtimeEligibility = salaryIncrement[0].eligible_for_overtime_salary
    else:
        # If no record for the given month, retrieve the latest entry
        salaryData = frappe.db.sql(
            """
            SELECT 
                tsh.from_date,
                tsh.salary,
                tas.eligible_for_overtime_salary
            FROM 
                `tabSalary History` AS tsh
            JOIN 
                `tabAssign Salary` AS tas
            ON 
                tsh.parent = tas.name
            WHERE 
                tas.employee_id = %s
                AND (YEAR(tsh.from_date) < %s 
                     OR (YEAR(tsh.from_date) = %s AND MONTH(tsh.from_date) <= %s))
            ORDER BY 
                tsh.from_date DESC
            LIMIT 1;
        """,
            (emp_id, year, year, month),
            as_dict=True,
        )
        if salaryData:
            basicSalary = salaryData[0].salary
            overtimeEligibility = salaryData[0].eligible_for_overtime_salary
        else:
            # Handle the case where no data is available
            basicSalary = 0.0
            overtimeEligibility = 0

    # Update and return the computed salary details
    salaryDetails["basicSalary"] = basicSalary
    salaryDetails["overtimeEligibility"] = overtimeEligibility
    return salaryDetails


# new logic to get shift deta
def getShiftDetails(attendanceDate, attendanceRecord):
    # Fetch shift details directly from attendanceRecord
    shift = attendanceRecord.get("shift")
    if not shift:
        raise ValueError("Shift is missing in attendance record")

    shiftStart = frappe.db.get_value("Shift Type", {"name": shift}, "start_time")
    shiftEnd = frappe.db.get_value("Shift Type", {"name": shift}, "end_time")
    if shiftStart is None or shiftEnd is None:
        raise ValueError(f"Shift details missing for shift {shift}")
    return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)


# provide checkIn and checkOut
def getAttendance(
    empId, shiftVariationRecord, attendanceDate, attendanceRecord, shiftDetails
):
    def to_datetime(att_date, t_obj):
        if isinstance(t_obj, datetime):
            return t_obj
        return datetime.combine(att_date, t_obj)

    idealCheckInTime = shiftDetails.get("idealCheckInTime")
    idealCheckOutTime = shiftDetails.get("idealCheckOutTime")

    actInTime = attendanceRecord.get("in_time")
    actOutTime = attendanceRecord.get("out_time")

    if not actInTime or not actOutTime:
        raise ValueError("Actual in_time or out_time is missing in attendance record")

    # Normalize attendanceDate
    if isinstance(attendanceDate, datetime):
        attendanceDateObj = attendanceDate.date()
    elif isinstance(attendanceDate, str):
        attendanceDateObj = datetime.strptime(attendanceDate, "%Y-%m-%d").date()
    else:
        attendanceDateObj = attendanceDate

    # Convert to datetime
    idealIn = to_datetime(attendanceDateObj, idealCheckInTime)
    idealOut = to_datetime(attendanceDateObj, idealCheckOutTime)
    actualIn = to_datetime(attendanceDateObj, actInTime)
    actualOut = to_datetime(attendanceDateObj, actOutTime)

    # Apply shift variation if applicable
    if shiftVariationRecord:
        for variation in shiftVariationRecord:
            if variation.get("attendance_date") != attendanceDateObj:
                continue

            employeeString = variation.get("employees")
            if employeeString:
                employeeList = [emp.strip() for emp in employeeString.split(",")]
                if empId not in employeeList:
                    continue

            shiftStart = variation.get("earliest_in_time")
            shiftEnd = variation.get("latest_out_time")

            if not shiftStart or not shiftEnd:
                raise ValueError(
                    f"Shift times missing for attendance date {attendanceDateObj}"
                )

            shiftStartDt = to_datetime(attendanceDateObj, shiftStart)
            shiftEndDt = to_datetime(attendanceDateObj, shiftEnd)

            if actualIn > shiftStartDt:
                diffIn = abs(actualIn - shiftStartDt)
                hours = diffIn.seconds // 3600
                minutes = (diffIn.seconds % 3600) // 60
                seconds = diffIn.seconds % 60

                actInTime = idealCheckInTime
                if hours:
                    actInTime += timedelta(hours=hours)
                if minutes:
                    actInTime += timedelta(minutes=minutes)
                if seconds:
                    actInTime += timedelta(seconds=seconds)
            else:
                actInTime = idealCheckInTime

            if actualOut >= shiftEndDt:
                diffOut = abs(shiftEndDt - idealOut)
                hours = diffOut.seconds // 3600
                minutes = (diffOut.seconds % 3600) // 60
                seconds = diffOut.seconds % 60

                actOutTime = idealCheckOutTime

    return {"in_time": actInTime, "out_time": actOutTime}


def getEncashment(empId, year, month):
    leaveEncashmentData = frappe.db.sql(
        """
            SELECT 
                name, 
                amount
            FROM 
                `tabPinnacle Leave Encashment`
            WHERE 
                employee = %s
                AND status = 'Unpaid'
                AND MONTH(to_date) = %s
                AND YEAR(to_date) = %s
            ORDER BY 
                upto DESC
            LIMIT 1
        """,
        (empId, month, year),
        as_dict=True,
    )

    if leaveEncashmentData:
        return leaveEncashmentData
    return []


# old logic to get shift details
# def getShiftDetails(empId, shiftVariationRecord, attendanceDate, attendanceRecord):
#     if shiftVariationRecord:
#         for shiftVariation in shiftVariationRecord:
#             if shiftVariation.get("attendance_date") == attendanceDate:
#                 employeeString = shiftVariation.get("employees")
#                 if employeeString:
#                     employeesList = employeeString.split(",")

#                     if (
#                         empId in employeesList
#                     ):  # Check if employees are missing or empty
#                         shiftStart = shiftVariation.get("earliest_in_time")
#                         shiftEnd = shiftVariation.get("latest_out_time")
#                         if shiftStart is None or shiftEnd is None:
#                             raise ValueError(
#                                 f"Shift times missing for attendance date {attendanceDate}"
#                             )
#                         return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)
#                     else:
#                         shift = attendanceRecord.get("shift")
#                         if not shift:
#                             raise ValueError("Shift is missing in attendance record")

#                         shiftStart = frappe.db.get_value(
#                             "Shift Type", {"name": shift}, "start_time"
#                         )
#                         shiftEnd = frappe.db.get_value(
#                             "Shift Type", {"name": shift}, "end_time"
#                         )
#                         if shiftStart is None or shiftEnd is None:
#                             raise ValueError(f"Shift details missing for shift {shift}")
#                         return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)
#                 else:
#                     shiftStart = shiftVariation.get("earliest_in_time")
#                     shiftEnd = shiftVariation.get("latest_out_time")
#                     if shiftStart is None or shiftEnd is None:
#                         raise ValueError(
#                             f"Shift times missing for attendance date {attendanceDate}"
#                         )
#                     return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)

#         shift = attendanceRecord.get("shift")
#         if not shift:
#             raise ValueError("Shift is missing in attendance record")

#         shiftStart = frappe.db.get_value("Shift Type", {"name": shift}, "start_time")
#         shiftEnd = frappe.db.get_value("Shift Type", {"name": shift}, "end_time")
#         if shiftStart is None or shiftEnd is None:
#             raise ValueError(f"Shift details missing for shift {shift}")
#         return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)
#     else:
#         # Fetch shift details directly from attendanceRecord
#         shift = attendanceRecord.get("shift")
#         if not shift:
#             raise ValueError("Shift is missing in attendance record")

#         shiftStart = frappe.db.get_value("Shift Type", {"name": shift}, "start_time")
#         shiftEnd = frappe.db.get_value("Shift Type", {"name": shift}, "end_time")
#         if shiftStart is None or shiftEnd is None:
#             raise ValueError(f"Shift details missing for shift {shift}")
#         return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)