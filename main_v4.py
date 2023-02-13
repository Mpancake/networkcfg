import paramiko
import csv
import os
import time

def write_to_csv(data):
    if 'output.csv' not in os.listdir(os.getcwd()):
        fl = open('output.csv','w',newline='',encoding='utf-8-sig')
        writer = csv.writer(fl)
        writer.writerow(['HOST','DESCR','BGP','OSPF','RPM','IP-MONITOR','VR-ENABLED','FORWARDING','RIB-GROUPS'])
        fl.close()

    fl = open('output.csv','a',newline='',encoding='utf-8-sig')
    writer = csv.writer(fl)
    writer.writerow(data)
    fl.close()

def process(ip,stdout,descr):
    bgp = 'no'
    ospf = 'no'
    services_rpm = 'no'
    ip_monitor = 'no'
    vr_enabled = 'no'
    fwd_enabled = 'no'
    rib_groups = 'no'

    if 'Backbone-Routers' in stdout:
        bgp = 'yes'
    if 'protocols ospf' in stdout:
        ospf = 'yes'
    if 'services rpm' in stdout:
        services_rpm = 'yes'
    if 'ip-monitor' in stdout:
        ip_monitor = 'yes'
    if 'instance-type virtual-router' in stdout:
        vr_enabled = 'yes'
    if 'instance-type forwarding' in stdout:
        fwd_enabled = 'yes'
    if 'routing-options rib-groups' in stdout:
        rib_groups = 'yes'

    write_to_csv([ip,descr,bgp,ospf,services_rpm,ip_monitor,vr_enabled,fwd_enabled,rib_groups])

def process_1(ip,stdout,ssh,comment,table_name):

    l = stdout.split('inet')
    for j in l:
        temp = j.split('\n')
        hops = []
        #print(temp)
        for q in temp:
            try:
                num = q.split('to')[-1].split(' via')[0]
                a = num.strip().replace('.','')
                int(a)
                hops.append(num.strip())
            except:
                pass


        if hops!=[]:
            commands = 'configure;'
            if len(hops)==2:
                if table_name!='inet.0':
                    commands+=f'delete routing-instances {table_name} routing-options static route 0/0;set routing-instances {table_name} routing-options static route 0/0 next-hop {hops[0]};set routing-instances {table_name} routing-options static route 0/0 qualified-next-hop {hops[1]} preference 25;delete services ip-monitoring;set services ip-monitoring policy ISP-1 then preferred-route route 0.0.0.0/0 next-hop {hops[1]};set services ip-monitoring policy ISP-1 match rpm-probe ISP-1;set services ip-monitoring policy ISP-2 then preferred-route route 0.0.0.0/0 next-hop {hops[0]};set services ip-monitoring policy ISP-2 match rpm-probe ISP-2;'
                else:
                    commands+=f'delete routing-instances {table_name} routing-options static route 0/0;set routing-instances {table_name} routing-options static route 0/0 next-hop {hops[0]};set routing-instances {table_name} routing-options static route 0/0 qualified-next-hop {hops[1]} preference 25;delete services ip-monitoring;set services ip-monitoring policy ISP-1 then preferred-route route 0.0.0.0/0 next-hop {hops[1]};set services ip-monitoring policy ISP-1 match rpm-probe ISP-1;set services ip-monitoring policy ISP-2 then preferred-route route 0.0.0.0/0 next-hop {hops[0]};set services ip-monitoring policy ISP-2 match rpm-probe ISP-2;'
            else:
                if table_name!='inet.0':
                    commands+=f'delete routing-instances {table_name} routing-options static route 0/0;set routing-instances {table_name} routing-options static route 0/0 next-hop {hops[0]};'
                else:
                    commands+=f'delete routing-options static route 0/0;set routing-options static route 0/0 next-hop {hops[0]};'

            print(f'[{ip}] Hops detected: {hops}')
            commands+=f'commit confirmed comment "{comment}";'
            commands+=f'run ping inet 1.1.1.1 rapid;'
            print(f'[{ip}] Executing command: \n{commands}\n')
            stdin, stdout, stderr = ssh.exec_command(commands)
            out = stdout.read().decode("utf-8")
            print(out)
            print(f'[{ip}] success commiting final comment')
            if '0% packet loss' in str(out):
                stdin, stdout, stderr = ssh.exec_command(f'configure;commit comment "{comment} _VALIDATED"')
                print(stdout.read())
            print('-'*40)

def main():

    data = open('input.csv','r').readlines()
    data = [[x.split(',')[-1].strip().split('/')[0],x.split(',')[-2].strip()] for x in data]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.banner_timeout = 200

    username = str(input('Username: '))
    password = str(input('Password: '))
    comment = str(input('Comment: '))
    category = int(input('1. Function: Gather Applied Configuration for RPM, Border, OSPF, VR, RIB-groups, and IP-monitoring\n2. Function: Read routing table and set static default to next-hops\nChoice: '))
    if category==2:
        table_name = str(input('Table name: '))
        if table_name=='':
            table_name = 'inet.0'
    for instance in data:
        ip,descr = instance
        try:
            target_host = ip
            target_port = 22
            print(f'>>> Connecting to {ip}')
            ssh.connect( hostname = target_host ,port = target_port , username = username, password = password)
            print(f'>>> Connected to {ip}')
            if category==2:
                stdin, stdout, stderr = ssh.exec_command(f'show route table {table_name} 0/0 exact')
                process_1(target_host,str(stdout.read().decode("utf-8")),ssh,comment,table_name)
                print(f'>>> Processed {ip} succesfully')
            else:
                ip,descr = instance
                try:
                    stdin, stdout, stderr = ssh.exec_command('show configuration | display set | no-more')
                    process(target_host,str(stdout.read().lower()),descr)
                    print(f'>>> Processed {ip} succesfully')
                except Exception as e:
                    print(f'>>> Error connecting to {ip}: {e}')
        except Exception as e:
            print(f'>>> Error connecting to {ip}: {e}')

main()
