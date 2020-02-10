#!/usr/bin/python2
# -*- coding: utf-8 -*-
# Rogue Access Point Detector
# version: 2.0
# author: anotherik (Ricardo Gonçalves)

##################################
#    Passive Detectors Module    #
##################################

# Supress Scapy IPv6 warning
import multiprocessing
import queue as Queue
import signal
from random import randint
import threading
import modules.logs.logs_api as logs_api
import modules.actuators.associate_model as associate
import modules.manage_interfaces as manage_interfaces
import modules.colors as colors
from scapy.all import *
import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


deauth_error_codes = {
    0: "Reserved.",
    1: "Unspecified reason.",
    2: "Previous authentication no longer valid.",
    3: "Deauthenticated because sending station (STA) is leaving or has left Independent Basic Service Set (IBSS) or ESS.",
    4: "Disassociated due to inactivity.",
    5: "Disassociated because WAP device is unable to handle all currently associated STAs.",
    6: "Class 2 frame received from nonauthenticated STA.",
    7: "Class 3 frame received from nonassociated STA.",
    8: "Disassociated because sending STA is leaving or has left Basic Service Set (BSS).",
    9: "STA requesting (re)association is not authenticated with responding STA.",
    10: "Disassociated because the information in the Power Capability element is unacceptable.",
    11: "Disassociated because the information in the Supported Channels element is unacceptable.",
    12: "Disassociated due to BSS Transition Management.",
    13: "Invalid element, that is, an element defined in this standard for which the content does not meet the specifications in Clause 8.",
    14: "Message integrity code (MIC) failure.",
    15: "4-Way Handshake timeout.",
    16: "Group Key Handshake timeout.",
    17: "Element in 4-Way Handshake different from (Re)Association Request/ Probe Response/Beacon frame.",
    18: "Invalid group cipher.",
    19: "Invalid pairwise cipher.",
    20: "Invalid AKMP.",
    21: "Unsupported RSNE version.",
    22: "Invalid RSNE capabilities.",
    23: "IEEE 802.1X authentication failed.",
    24: "Cipher suite rejected because of the security policy."
}


def signal_handler(signal, frame):
    try:
        manage_interfaces.disable_monitor(interface_monitor)
    except Exception as err:
        logs_api.errors_log(str(err))
        pass

    print(colors.get_color("GRAY") +
          "\nExiting...\nGoodbye!"+colors.get_color("ENDC"))
    sys.exit(0)


TIMEOUT = 5  # wait 5 second before skipping association process


def interrupted(signum, frame):
    print(colors.get_color("GRAY") +
          'Skipping association...'+colors.get_color("ENDC"))
    sys.exit(0)


def yes_or_no():
    try:
        signal.signal(signal.SIGALRM, interrupted)
        assoc = str(raw_input())
        return assoc
    except:
        pass


def authorized_aps(scanned_ap, profile):

    with open(profile, 'r') as f:
        next(f)  # skipping first line
        t = 0
        for line in f:

            auth_ssid, auth_enc, auth_rssi, auth_ch = line.split()[0], line.split()[
                1], line.split()[2], line.split()[3]
            auth_rssi = int(auth_rssi)
            auth_ch = int(auth_ch)
            nr_auth_aps = int(line.split()[4])

            if (scanned_ap['essid'] == auth_ssid):
                auth_bssids = []
                c = 5
                while c < len(line.split()):
                    auth_bssids.append(line.split()[c])
                    c += 1

                if(c > 6):
                    t = c-6

                # DEBUG
                #print ("scanned ap: %s" % scanned_ap['mac'])
                #print ("auth bssids: %s" % auth_bssids)
                if (scanned_ap['mac'] in auth_bssids):  # (.lower())

                    if (auth_enc != 'Open' and scanned_ap['key type'] == "Open"):
                        print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] Evil Twin, different encryption." % (
                            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                        break
                    if (auth_ch != int(scanned_ap['channel'])):
                        print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] Multichannel AP." % (
                            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                        break
                    if (abs(int(scanned_ap['signal'])) > auth_rssi+15 or abs(int(scanned_ap['signal'])) < auth_rssi-15):
                        print(colors.get_color("FAIL")+"[%s | %s] Strange RSSI!!! Associate? (y/n)" % (
                            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

                        ##print ("the timeout: %s" % TIMEOUT)
                        signal.alarm(TIMEOUT)
                        assoc = yes_or_no()
                        signal.alarm(0)

                        if(assoc == "y"):
                            iface = str(
                                raw_input("Choose an interface for the association process: "))
                            if (scanned_ap['key type'] == "Open"):
                                p = multiprocessing.Process(associate.associateToAp(
                                    scanned_ap['essid'], scanned_ap['mac'], '', iface))
                                p.start()
                            else:
                                pwd = str(raw_input("Enter the AP password: "))
                                p = multiprocessing.Process(associate.associateToAp(
                                    scanned_ap['essid'], scanned_ap['mac'], pwd, iface))
                                p.start()
                        else:
                            break
                else:

                    t += 1
                    # print "t = %s and nr_auth_aps = %s" % (t,nr_auth_aps)
                    if (t == nr_auth_aps):
                        print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] Evil Twin, unauthorized bssid." % (
                            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

            # Testing Network
            if (scanned_ap['essid'] == "LAB_NETWORK"):
                print(colors.get_color("FAIL")+"[%s | %s] Associate? (y/n)" % (
                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

                signal.alarm(TIMEOUT)
                assoc = yes_or_no()
                signal.alarm(0)

                if(assoc == "y"):
                    iface = str(
                        raw_input("Choose an interface for the association process: "))
                    if (scanned_ap['key type'] == "Open"):
                        p = multiprocessing.Process(associate.associateToAp(
                            scanned_ap['essid'], scanned_ap['mac'], '', iface))
                        p.start()
                    else:
                        pwd = str(raw_input("Enter the AP password: "))
                        p = multiprocessing.Process(associate.associateToAp(
                            scanned_ap['essid'], scanned_ap['mac'], pwd, iface))
                        p.start()
                else:
                    break


phishing_karma = {}


def spot_karma(scanned_ap):
    # DEBUG
    #print("Looking fot karmas...")
    # print phishing_karma
    #print (scanned_ap['mac'] in phishing_karma and scanned_ap['essid'] not in phishing_karma)

    if (scanned_ap['mac'] in phishing_karma):
        c = len(phishing_karma.values())
        cp = 0
        for i in range(c):
            if (scanned_ap['essid'] in phishing_karma.values()[i] and scanned_ap['mac'] in phishing_karma.values()[i]):
                break
            #print ("scanned_ap %s" % scanned_ap['essid'])
            #print ("phishing_karma: %s" % phishing_karma.values()[i])
            if (scanned_ap['essid'] not in phishing_karma.values()[i]):
                cp += 1
            if (cp == c):
                phishing_karma[scanned_ap['mac']].add(scanned_ap['essid'])
                print(colors.get_color("FAIL")+"[%s | %s] Karma Rogue Access Point!\n[Type] Karma attack." % (
                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                break
    else:
        phishing_karma[scanned_ap['mac']] = set([scanned_ap['essid']])


def gen_random_ssid():
    N = 6
    SSID = ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for _ in range(N))
    return SSID


pineAP_ssids = []


def gen_PineAp_ssid(scanned_ap):

    # change to find by bssid!
    default_name = "Pineapple"
    default_bssid = ":13:37:"
    # if(default_name in scanned_ap['essid'] and scanned_ap['key type'] == "Open"): #based from neighbour Open networks around
    if(default_bssid in scanned_ap['mac'] and scanned_ap['key type'] == "Open"):
        prefix = scanned_ap['mac'][12:].replace(":", "")
        pineAP_ssids.append(default_name+"_"+prefix)

    # print pineAP_ssids
    # random prefix
    rand_prefix = ''.join(random.choice('0123456789ABCDEF') for i in range(4))
    pineAP_ssids.append(default_name+"_"+rand_prefix)


def send_Probe_Req(interface):

    for pineAP_ssid in pineAP_ssids:
        # DEBUG
        #print("Probing for %s" % pineAP_ssid)

        broadcast = ":".join(["ff"]*6)
        rand_bssid = new_mac = ':'.join(
            ['%02x' % x for x in list(map(lambda x:randint(0, 255), range(6)))])

        radioTapHeader = RadioTap()
        dot11Header = Dot11(
            addr1=broadcast, addr2=rand_bssid, addr3=rand_bssid)
        dot11ProbeReq = Dot11ProbeReq()
        dot11Elt = Dot11Elt(ID=0, info=pineAP_ssid)

        pkt = radioTapHeader / dot11Header / dot11ProbeReq / dot11Elt
        sendp(pkt, iface=interface, verbose=0)  # , verbose=0


def spoting_PineAP(*arg):
    global interface_monitor

    scanned_ap = arg[0]
    active_probing = False
    alfa_brand = "Alfa"
    default_bssid = ":13:37:"
    if (default_bssid in scanned_ap['mac']):
        print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] PineAp RAP. (Acc: 1)" % (
            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

    elif (default_bssid in scanned_ap['mac'] and scanned_ap['key type'] == "Open"):
        print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] PineAp RAP. (Acc: 2)" % (
            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

    elif (alfa_brand in scanned_ap['manufacturer']):
        print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] Blacklisted BSSID. (Acc: 1)" % (
            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

    if(len(arg) > 2):

        active_probing = arg[1]
        interface_monitor = arg[2]

        th1 = threading.Thread(target=gen_PineAp_ssid(scanned_ap))
        th1.daemon = True
        th1.start()
        #p1 = multiprocessing.Process(target=gen_PineAp_ssid, args=(scanned_ap,))
        # p1.start()
        # p1.join()

        if(active_probing):
            th2 = threading.Thread(target=send_Probe_Req(interface_monitor))
            th2.daemon = True
            th2.start()
            #p2 = multiprocessing.Process(target=send_Probe_Req, args=(interface_monitor,))
            # p2.start()
            # p2.join()

    for pineAP_ssid in pineAP_ssids:
        if(pineAP_ssid == scanned_ap['essid']):
            print(colors.get_color("FAIL")+"[%s | %s] Possible Rogue Access Point!\n[Type] PineAp produced RAP (possible hidden RAP)." % (
                scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
            active_probing = False


def free_WiFis_detect(scanned_ap, captured_aps):
    # DEBUG
    #print("Detecting Rogue Free Wifis ...")

    with open('profiles/free_wifis.txt', 'r') as f:
        next(f)
        for line in f:
            auth_ssid = line.split()[0]

            # print(auth_ssid)
            ##print (scanned_ap['essid'])

            if (auth_ssid in scanned_ap['essid']):
                print(colors.get_color("UNDERLINE")+"Scanning %s " %
                      scanned_ap['essid'] + " with: %s" % scanned_ap['mac']+colors.get_color("ENDC"))
                ##print("inside 1")
                auth_vendors = []
                c = 1
                while c < len(line.split()):
                    auth_vendors.append(line.split()[c])
                    c += 1

                # print scanned_ap['manufacturer']
                ##print ("AUTH VENDORS: %s" % auth_vendors)

                if (scanned_ap['manufacturer'] in auth_vendors):
                    ##print("inside 2 **************************")

                    # in this situation we need to understand the pattern of the bssid and channel
                    # if ("STCP" in captured_ap['essid']):
                    ##	print (colors.get_color("OKGREEN")+"[%s | %s] Probable Auth Free WiFi." % (scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

                    for captured_ap in captured_aps:
                        ##print("inside 3 +++++++++++++++++++++++")

                        # NOS_WIFI
                        if(scanned_ap['essid'] == "NOS_WIFI_Fon" and ("NOS-" in captured_ap['essid'] or "ZON-" in captured_ap['essid'])):

                            last_byte = captured_ap['mac'][15:]
                            val = int(last_byte, base=16)
                            val_inc = hex(val + 1)[2:]
                            correct_bssid = captured_ap['mac'][:-2] + val_inc

                            # DEBUG
                            ##print("Produced correct BSSID: %s and CH: %s" % (correct_bssid, captured_ap['channel']))
                            ##print("Scanned AP BSSID: %s and CH: %s" % (scanned_ap['mac'], scanned_ap['channel']))
                            if (scanned_ap['mac'] == correct_bssid.upper() and scanned_ap['channel'] == captured_ap['channel']):
                                print(colors.get_color("OKGREEN")+"[%s | %s] Probable Valid Free WiFi." % (
                                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                                break
                            # else: # not in auth vendors
                            #	print(colors.get_color("FAIL")+"[%s | %s] Strange Free WiFi. Possible Rogue Access Point!" % (scanned_ap['essid'], scanned_ap['mac']) +colors.get_color("ENDC") )
                            #	break

                        # MEO-WiFi
                        elif(scanned_ap['essid'] == "MEO-WiFi" and "MEO-" in captured_ap['essid']):

                            first_byte = captured_ap['mac'][:-15]
                            last_byte = captured_ap['mac'][15:]
                            val_1 = int(first_byte, base=16)
                            val_1_inc = hex(val_1 + 2)[2:]
                            val_2 = int(last_byte, base=16)
                            val_2_inc = hex(val_2 + 1)[2:]

                            correct_bssid = val_1_inc + \
                                captured_ap['mac'][2:-2] + val_2_inc

                            # DEBUG
                            ##print("Produced correct BSSID: %s and CH: %s" % (correct_bssid, captured_ap['channel']))
                            ##print("Scanned AP BSSID: %s and CH: %s" % (scanned_ap['mac'], scanned_ap['channel']))
                            if (scanned_ap['mac'] == correct_bssid.upper() and scanned_ap['channel'] == captured_ap['channel']):
                                print(colors.get_color("OKGREEN")+"[%s | %s] Probable Valid Free WiFi." % (
                                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                                break
                            # else: # not in auth vendors
                            #	print(colors.get_color("FAIL")+"[%s | %s] Strange Free WiFi. Possible Rogue Access Point!" % (scanned_ap['essid'], scanned_ap['mac']) +colors.get_color("ENDC") )
                            #	break

                        # wifi_eventos
                        elif(scanned_ap['essid'] == "wifi_eventos" and "eduroam" in captured_ap['essid']):

                            last_byte = captured_ap['mac'][15:]
                            val = int(last_byte, base=16)
                            val_inc = hex(val + 1)[2:]
                            correct_bssid = captured_ap['mac'][:-2] + val_inc

                            # DEBUG
                            ##print("Produced correct BSSID: %s and CH: %s" % (correct_bssid, captured_ap['channel']))
                            ##print("Scanned AP BSSID: %s and CH: %s" % (scanned_ap['mac'], scanned_ap['channel']))
                            if (scanned_ap['mac'] == correct_bssid.upper() and scanned_ap['channel'] == captured_ap['channel']):
                                print(colors.get_color("OKGREEN")+"[%s | %s] Probable Valid Free WiFi." % (
                                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                                break
                            else:  # not in auth vendors
                                print(colors.get_color("FAIL")+"[%s | %s] Strange Free WiFi. Possible Rogue Access Point!" % (
                                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                                break

                        # UPorto
                        elif(scanned_ap['essid'] == "UPorto" and "eduroam" in captured_ap['essid']):

                            last_byte = captured_ap['mac'][15:]
                            val = int(last_byte, base=16)
                            val_inc = hex(val + 2)[2:]
                            correct_bssid = captured_ap['mac'][:-2] + val_inc

                            # DEBUG
                            ##print("Produced correct BSSID: %s and CH: %s" % (correct_bssid, captured_ap['channel']))
                            ##print("Scanned AP BSSID: %s and CH: %s" % (scanned_ap['mac'], scanned_ap['channel']))
                            if (scanned_ap['mac'] == correct_bssid.upper() and scanned_ap['channel'] == captured_ap['channel']):
                                print(colors.get_color("OKGREEN")+"[%s | %s] Probable Valid Free WiFi." % (
                                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                                break
                            else:  # not in auth vendors
                                print(colors.get_color("FAIL")+"[%s | %s] Strange Free WiFi. Possible Rogue Access Point!" % (
                                    scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
                                break

                else:  # not in auth vendors
                    print(colors.get_color("FAIL")+"[%s | %s] Strange Free WiFi. Possible Rogue Access Point!" % (
                        scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))


def getTimeDate():
    return time.strftime("%X") + " " + time.strftime("%x")


def sniffRequests(p):
    global auth_reqs
    global assoc_reqs

    if (p.haslayer(Dot11Auth)):
        print(colors.get_color("BOLD")+"[%s] " % getTimeDate() + colors.get_color("OKGREEN") +
              "Authentication packet found from %s to %s" % (p[Dot11].addr2, p[Dot11].addr1) + colors.get_color("ENDC"))
        auth_reqs += 1
    if (p.haslayer(Dot11AssoReq)):
        print(colors.get_color("BOLD")+"[%s] " % getTimeDate() + colors.get_color("OKBLUE") +
              "Association request found from %s to %s" % (p[Dot11].addr2, p[Dot11].addr1) + colors.get_color("ENDC"))
        assoc_reqs += 1
    if (p.haslayer(Dot11Deauth)):
        print(colors.get_color("BOLD")+"[%s] " % getTimeDate() + colors.get_color("PURPLE") + "Deauthentication packet found from %s to %s Reason -> %s" % (
            p[Dot11].addr2, p[Dot11].addr1, p[Dot11Deauth].reason) + colors.get_color("ENDC")),
        error_code = int(p[Dot11Deauth].reason)
        print(deauth_error_codes[error_code])

    if(auth_reqs >= 20):
        print(colors.get_color(
            "FAIL")+"[WiFi Attack] Probable PMKID attack.\nReason: Too many Authentication requests." + colors.get_color("ENDC"))
        auth_reqs = 0
    if(assoc_reqs >= 20):
        print(colors.get_color(
            "FAIL")+"[WiFi Attack] Probable PMKID attack.\nReason: Too many Association requests." + colors.get_color("ENDC"))
        assoc_reqs = 0

    signal.signal(signal.SIGINT, signal_handler)


def wifi_attacks_detector(interface):
    global interface_monitor
    interface_monitor = interface
    global auth_reqs
    global assoc_reqs
    auth_reqs = 0
    assoc_reqs = 0
    print(colors.get_color("GRAY") +
          "WiFi Attacks Detection..."+colors.get_color("ENDC"))
    sniff(iface=interface_monitor, prn=sniffRequests, store=0)


def check_tsf(scanned_ap):

    simple_poc_threshold_down = "0:01:00.10"
    simple_poc_threshold_up = 800

    scanned_tsf = scanned_ap['tsf'].split()[0]

    if (scanned_tsf < simple_poc_threshold_down):
        print(colors.get_color("ORANGE")+"[%s | %s] Recently Created AP..." % (
            scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))

    if (len(scanned_ap['tsf'].split()) > 1):
        if (int(scanned_tsf) > simple_poc_threshold_up):
            print(colors.get_color("ORANGE")+"[%s | %s] Strange uptime..." % (
                scanned_ap['essid'], scanned_ap['mac']) + colors.get_color("ENDC"))
