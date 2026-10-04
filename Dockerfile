FROM quay.io/keycloak/keycloak:26.1

USER root
COPY infra/keycloak/parcham-realm.json /opt/keycloak/data/import/parcham-realm.json
COPY infra/stage/keycloak-start.sh /opt/keycloak/bin/parcham-stage-start.sh
RUN chmod +x /opt/keycloak/bin/parcham-stage-start.sh
USER 1000

ENTRYPOINT ["/opt/keycloak/bin/parcham-stage-start.sh"]
