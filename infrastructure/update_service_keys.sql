INSERT INTO servicekey (name, service, metadata, kid, jwk, created_date, expiration_date) 
    VALUES ('quay-readonly', 
                'quay', 
                '{}', 
                '$QUAY_READONLY_KID', 
                '$QUAY_READONLY_JWK', 
                '2024-01-01 00:00:00', 
                '2025-01-01 00:00:00');

INSERT INTO servicekeyapproval (approved_date, approval_type, notes)
    VALUES ('2024-01-01 00:00:00', 'Quay Readonly Service Key', 'approval notes');

UPDATE servicekey SET approval_id=servicekeyapproval.id FROM servicekeyapproval 
    WHERE servicekey.name = 'quay-readonly' AND servicekeyapproval.approval_type='Quay Readonly Service Key';