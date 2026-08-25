import pytest
from engine.rule_checker import validate_network_state

def test_admin_down_rule():
    show_output = "GigabitEthernet0/1 is administratively down, line protocol is down"
    findings = validate_network_state("Interface not working", "", show_output)
    
    assert any(f.rule_key == "R01_ADMIN_DOWN" for f in findings)
    
def test_no_faults_rule():
    show_output = "All good here"
    findings = validate_network_state("Something", "", show_output)
    
    assert any(f.rule_key == "R00_NO_FAULTS" for f in findings)
    
def test_duplicate_ip():
    show_output = "Duplicate address 192.168.1.1 on 0000.1111.2222, Ethernet0/0"
    findings = validate_network_state("IP conflict", "", show_output)
    
    assert any(f.rule_key == "R07_DUP_IP" for f in findings)
