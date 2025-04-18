FROM ubuntu:latest AS build
RUN apt-get update
RUN apt-get install curl default-jre -y
WORKDIR /kafka-test
RUN curl -o kafka.tgz https://dlcdn.apache.org/kafka/3.7.0/kafka_2.13-3.7.0.tgz
RUN tar -xzf kafka.tgz --strip-components=1