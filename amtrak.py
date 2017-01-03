import requests
from bs4 import BeautifulSoup


def get_args(**kwargs):
    data = {
        "requestor": "amtrak.presentation.handler.page.rail.AmtrakRailFareFinderPageHandler",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/@bookpath": "farefamilies",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/allJourneyRequirements/@ff_tab_selected": "bookatrip",
        "xwdf_TripType": "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/tripType",
        "wdf_TripType": "OneWay",
        "xwdf_TripType": "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/tripType",
        "xwdf_origin": "/sessionWorkflow/productWorkflow[@product='Rail']/travelSelection/journeySelection[1]/departLocation/search",
        "wdf_origin": kwargs.get("origin") or "",
        "xwdf_destination": "/sessionWorkflow/productWorkflow[@product='Rail']/travelSelection/journeySelection[1]/arriveLocation/search",
        "wdf_destination": kwargs.get("dest") or "",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/journeyRequirements[1]/departDate.usdate": kwargs.get("date") or "",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/journeyRequirements[1]/departTime.hourmin": kwargs.get("time") or "",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/journeyRequirements[2]/departDate.usdate": "",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/journeyRequirements[2]/departTime.hourmin": "",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/allJourneyRequirements/numberOfTravellers[@key='Adult']": kwargs.get("adult") or "1",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/allJourneyRequirements/numberOfTravellers[@key='Senior']": kwargs.get("senior") or "0",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/allJourneyRequirements/numberOfTravellers[@key='Child']": kwargs.get("child") or "0",
        "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/allJourneyRequirements/numberOfTravellers[@key='Infant']": kwargs.get("infant") or "0",
        "xwdf_BookType": "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/@booktype",
        "wdf_BookType": "",
        "xwdf_BookType": "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/@booktype",
        "xwdf_promoCode": "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/couponRequirements/coupon/code",
        "wdf_promoCode": "Promo Code",
        "_handler=amtrak.presentation.handler.request.rail.farefamilies.AmtrakRailFareFamiliesSearchRequestHandler/_xpath=/sessionWorkflow/productWorkflow[@product='Rail'].x": "41",
        "_handler=amtrak.presentation.handler.request.rail.farefamilies.AmtrakRailFareFamiliesSearchRequestHandler/_xpath=/sessionWorkflow/productWorkflow[@product='Rail'].y": "7"
    }

    for i in range(1, int(kwargs.get("student", 0))+1):
        data.update({
            "xwdf_person_type{}".format(i): "/sessionWorkflow/productWorkflow[@product='Rail']/tripRequirements/allJourneyRequirements/person[{}]/personType".format(i),
            "wdf_person_type{}".format(i): "Student",
        })

    return data

def fmt(s):
    return s.strip().replace('\r\n', '')

def get_price_id(soup, id):
    jsid = id.split('upgradePrice')[1]
    jsdef = "jnyPrice['{}']".format(jsid)
    for scr in soup.select("script"):
        if jsdef in scr.text:
            line = scr.text.split(jsdef)[1]
            line = line.split('"]')[0]
            line = line.split('["')[1]
            if line[0] != "$":
                return "$" + line
            return line
    return "(unknown)"

def return_results(**args):
    r = requests.post("https://tickets.amtrak.com/itd/amtrak",
                      params=get_args(**args),
                      headers={"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:0.9.4.1) Gecko/20020508 Netscape6/6.2.3",})
    soup = BeautifulSoup(r.text, "lxml")
    errors = soup.select("div#amtrak_error_id")

    result = {"results": [], "errors": [], "args": args}
    for e in errors:
        result["errors"].append(e.text)

    options = soup.select("table.ffam-fare-family")
    result["num"] = len(options)
    for o in options:
        r = {}
        addCartSoldOut = o.select_one(".ffam-button-container")
        if addCartSoldOut.select_one(".ffam-cancelled"):
            r["cancelled"] = True
        elif addCartSoldOut.select_one(".ffam-add-to-cart"):
            r["cancelled"] = False
        segment = o.select_one(".ffam-segment-container")
        col1 = segment.select_one(".ffam-first-col")
        if col1:
            r["time"] = fmt(col1.select_one(".ffam-time").text)
            r["train"] = {
                "name": fmt(col1.select_one(".ffam-train-name-padding").text),
                "id": col1.select_one(".ffam-train-name-container").attrs['id']
            }
        icons = o.select(".ffam-icons a img")
        r["amenities"] = []
        for i in icons:
            src = i.attrs['src']
            name = src.split('amenities_')[1].split('.')[0]
            r["amenities"].append(name)

        fareOpts = []
        fareFamilies = soup.select_one("table.ffam-fare-family-header").select(".ffam-family")
        for f in fareFamilies:
            fareOpts.append({
                "fareType": fmt(f.text)
            })
        ffrows = o.select("tr.ffam-prices-container > td")
        findex = -1
        for f in ffrows:
            pr = f.select_one(".ffam-price-container")

            if pr:
                price = fmt(pr.text)
                if len(price) < 1:
                    price = get_price_id(soup, pr.select_one("span").attrs['id'])
                    fareOpts[findex]["price_js"] = True
                fareOpts[findex]["available"] = True
                fareOpts[findex]["price"] = price
            elif findex >= 0:
                fareOpts[findex]["available"] = False
            findex += 1
        
        ffseg = o.select(".ffam-segment-container > td")
        #ffseg = [o.select_one(".ffam-segment-container .ffam-{}-col".format(i)) for i in ['second', 'third', 'fourth', 'last']]
        findex = -1
        for f in ffseg:
            seats = f.select_one(".ffam-seats")
            if seats:
                if seats.select_one(".ffam-soldout-notoffered"):
                    fareOpts[findex]["soldout"] = True
                else:
                    fareOpts[findex]["soldout"] = False
                    fareOpts[findex]["seats"] = fmt((seats.select_one(".ffam-room-name") or seats.select_one("a")).text)
            notices = f.select_one(".notices")
            if notices:
                if notices.select_one(".ffam-limited"):
                    fareOpts[findex]["limited"] = True
                txt = fmt(notices.text)
                if len(txt) > 0:
                    fareOpts[findex]["notice"] = txt
            findex += 1
        
        r["fares"] = fareOpts

        result["results"].append(r)

    return result
