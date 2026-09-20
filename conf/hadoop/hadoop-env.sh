# Bien moi truong cho cac tien trinh Hadoop.
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"
export HADOOP_HEAPSIZE_MAX=1g

# Java 17 khoa truy cap noi bo module; Hadoop can mo lai mot so goi.
OPENS="--add-opens=java.base/java.lang=ALL-UNNAMED"
OPENS="${OPENS} --add-opens=java.base/java.util=ALL-UNNAMED"
OPENS="${OPENS} --add-opens=java.base/java.util.concurrent=ALL-UNNAMED"
OPENS="${OPENS} --add-opens=java.base/java.io=ALL-UNNAMED"
OPENS="${OPENS} --add-opens=java.base/java.nio=ALL-UNNAMED"
OPENS="${OPENS} --add-opens=java.base/sun.nio.ch=ALL-UNNAMED"
export HADOOP_OPTS="${HADOOP_OPTS:-} ${OPENS}"
