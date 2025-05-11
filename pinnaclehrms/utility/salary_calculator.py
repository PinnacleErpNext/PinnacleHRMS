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
                    "employee_id": data.get("employee"),
                    "employee_name": data.get("employee_name"),
                    "personal_email": data.get("personal_email"),
                    "designation": data.get("designation"),
                    "department": data.get("department"),
                    "pan_number": data.get("pan_number"),
                    "date_of_joining": data.get("date_of_joining"),
                    "attendance_device_id": data.get("attendance_device_id"),
                    "basic_salary": data.get("basic_salary"),
                    "per_day_salary": salaryInfo.get("per_day_salary"),
                    "standard_working_days": salaryInfo.get("standard_working_days"),
                    "others_days": salaryInfo.get("others"),
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
            if salaryInfo.get("others"):
                paySlip.append(
                    "salary_calculation",
                    {
                        "particulars": "Others Day",
                        "days": salaryInfo.get("others"),
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


def getEmpRecords(data):

    # Construct the base query
    baseQuery = """
            SELECT
                e.company,
                e.employee,
                e.employee_name,
                e.personal_email,
                e.designation,
                e.department,
                e.pan_number,
                e.date_of_joining,
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
                e.status = "Active" AND YEAR(a.attendance_date) = %s AND MONTH(a.attendance_date) = %s
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
    if data.get("select_employee"):
        employee = data.get("select_employee")
        baseQuery += "AND e.employee = %s"
        filters.append(employee)

    date = f"{year}-{month:02d}-01"

    records = frappe.db.sql(baseQuery, filters, as_dict=False)
    if not records:
        return frappe.throw("No records found!")

    # Initialize a defaultdict to organize employee records
    empRecords = defaultdict(
        lambda: {
            "company": "",
            "employee": "",
            "employee_name": "",
            "personal_email": "",
            "designation": "",
            "department": "",
            "pan_number": "",
            "date_of_joining": "",
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
            personal_email,
            designation,
            department,
            pan_number,
            date_of_joining,
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
                "personal_email": personal_email,
                "designation": designation,
                "department": department,
                "pan_number": pan_number,
                "date_of_joining": date_of_joining,
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


def getShiftDetails(empId, shiftVariationRecord, attendanceDate, attendanceRecord):
    if shiftVariationRecord:
        for shiftVariation in shiftVariationRecord:
            if shiftVariation.get("attendance_date") == attendanceDate:
                employeeString = shiftVariation.get("employees")
                if employeeString:
                    employeesList = employeeString.split(",")

                    if (
                        empId in employeesList
                    ):  # Check if employees are missing or empty
                        shiftStart = shiftVariation.get("earliest_in_time")
                        shiftEnd = shiftVariation.get("latest_out_time")
                        if shiftStart is None or shiftEnd is None:
                            raise ValueError(
                                f"Shift times missing for attendance date {attendanceDate}"
                            )
                        return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)
                    else:
                        shift = attendanceRecord.get("shift")
                        if not shift:
                            raise ValueError("Shift is missing in attendance record")

                        shiftStart = frappe.db.get_value(
                            "Shift Type", {"name": shift}, "start_time"
                        )
                        shiftEnd = frappe.db.get_value(
                            "Shift Type", {"name": shift}, "end_time"
                        )
                        if shiftStart is None or shiftEnd is None:
                            raise ValueError(f"Shift details missing for shift {shift}")
                        return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)
                else:
                    shiftStart = shiftVariation.get("earliest_in_time")
                    shiftEnd = shiftVariation.get("latest_out_time")
                    if shiftStart is None or shiftEnd is None:
                        raise ValueError(
                            f"Shift times missing for attendance date {attendanceDate}"
                        )
                    return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)

        shift = attendanceRecord.get("shift")
        if not shift:
            raise ValueError("Shift is missing in attendance record")

        shiftStart = frappe.db.get_value("Shift Type", {"name": shift}, "start_time")
        shiftEnd = frappe.db.get_value("Shift Type", {"name": shift}, "end_time")
        if shiftStart is None or shiftEnd is None:
            raise ValueError(f"Shift details missing for shift {shift}")
        return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)
    else:
        # Fetch shift details directly from attendanceRecord
        shift = attendanceRecord.get("shift")
        if not shift:
            raise ValueError("Shift is missing in attendance record")

        shiftStart = frappe.db.get_value("Shift Type", {"name": shift}, "start_time")
        shiftEnd = frappe.db.get_value("Shift Type", {"name": shift}, "end_time")
        if shiftStart is None or shiftEnd is None:
            raise ValueError(f"Shift details missing for shift {shift}")
        return calculateShiftTimes(attendanceDate, shiftStart, shiftEnd)


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
        others = 0
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

        shiftVariationRecord = frappe.db.sql(
            """SELECT 
                                                    svh.date AS attendance_date,
                                                    GROUP_CONCAT(DISTINCT sv.name) AS shift_variation_names,
                                                    sv.year,
                                                    sv.month_num,
                                                    GROUP_CONCAT(DISTINCT sfe.employee) AS employees,
                                                    MIN(svh.in_time) AS earliest_in_time,
                                                    MAX(svh.out_time) AS latest_out_time
                                                FROM 
                                                    `tabShift Variation` AS sv
                                                LEFT JOIN 
                                                    `tabShift variation history` AS svh 
                                                    ON sv.name = svh.parent
                                                LEFT JOIN 
                                                    `tabShift for employee` AS sfe 
                                                    ON sv.name = sfe.parent
                                                WHERE 
                                                    sv.year = %s
                                                    AND sv.month_num = %s
                                                GROUP BY 
                                                    svh.date;
                                            """,
            (year, month),
            as_dict=True,
        )

        dojStr = data.get("date_of_joining")
        doj = (
            datetime.strptime(dojStr, "%Y-%m-%d") if isinstance(dojStr, str) else dojStr
        )

        currentDate = datetime.today().date()
        workingPeriod = (relativedelta(currentDate, doj)).years
        leaveEncashmentData = frappe.db.get_list(
            "Pinnacle Leave Encashment",
            filters={"employee": emp_id},
            fields=["amount"],
            order_by="upto desc",
            limit=1,
            as_list=True,
        )
        if len(leaveEncashmentData) > 0:
            leaveEncashmentAmount = leaveEncashmentData[0][0]

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

                shiftDetails = getShiftDetails(
                    emp_id, shiftVariationRecord, attendanceDate, attendanceRecord
                )

                idealCheckInTime = shiftDetails.get("idealCheckInTime")
                idealCheckOutTime = shiftDetails.get("idealCheckOutTime")
                overtimeThreshold = shiftDetails.get("overtimeThreshold")

                if inTime and outTime:
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

                        totalSalary += salary

                        if checkIn > idealCheckInTime and (
                            deductionPercentage == 0.1 or deductionPercentage == 0.2
                        ):
                            if lates < allowedLates:
                                totalSalary += perDaySalary * 0.1

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
                                        "salary": salary,
                                        "status": status,
                                    }
                                )
                            else:
                                fullDays += 1
                                actualWorkingDays += 1
                                status = "Full Days"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": salary,
                                        "status": status,
                                    }
                                )
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
                                        "salary": salary,
                                        "status": status,
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
                                            "salary": salary,
                                            "status": status,
                                        }
                                    )
                                else:
                                    allowedLates -= 1
                                    actualWorkingDays += 1
                                    fullDays += 1
                                    status = "Full Day"
                                    empAttendanceRecord.append(
                                        {
                                            "date": attendanceDate,
                                            "deductionPercentage": deductionPercentage,
                                            "salary": salary,
                                            "status": status,
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
                                        "salary": salary,
                                        "status": status,
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
                                        "salary": salary,
                                        "status": status,
                                    }
                                )
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
                                        "salary": salary,
                                        "status": status,
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
                                        "salary": salary,
                                        "status": status,
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
                                        "salary": salary,
                                        "status": status,
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
                                        "salary": salary,
                                        "status": status,
                                    }
                                )
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
                                        "salary": salary,
                                        "status": status,
                                    }
                                )
                            else:
                                others += 1
                                actualWorkingDays += 1
                                status = "Others"
                                empAttendanceRecord.append(
                                    {
                                        "date": attendanceDate,
                                        "deductionPercentage": deductionPercentage,
                                        "salary": salary,
                                        "status": status,
                                    }
                                )
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
                                    "salary": salary,
                                    "status": status,
                                }
                            )
                    # print(today, deductionPercentage, salary)
                else:
                    if any(holiday["holiday_date"] == today for holiday in holidays):
                        pass
                    else:
                        totalAbsents += 1
                        status = "Absent"
                        empAttendanceRecord.append(
                            {
                                "date": attendanceDate,
                                "deductionPercentage": 1,
                                "salary": salary,
                                "status": status,
                            }
                        )
            else:
                if any(holiday["holiday_date"] == today for holiday in holidays):
                    pass
                else:
                    totalAbsents += 1
                    status = "Absent"
                    empAttendanceRecord.append(
                        {
                            "date": attendanceDate,
                            "deductionPercentage": 1,
                            "salary": salary,
                            "status": status,
                        }
                    )

        totalSalary -= totalLateDeductions
        if actualWorkingDays > 0:
            totalSalary += overtimeSalary + holidayAmount + leaveEncashmentAmount
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
            "others": others,
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
                print(basicSalary)
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
