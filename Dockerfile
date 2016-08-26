FROM ubuntu:14.04
MAINTAINER Anand Ramakrishna <anandram@microsoft.com>
RUN echo "deb http://archive.ubuntu.com/ubuntu/ trusty main universe" >> /etc/apt/sources.list
RUN apt-get update
RUN apt-get --assume-yes install build-essential 
RUN apt-get --assume-yes install autoconf
RUN apt-get --assume-yes install git
RUN apt-get --assume-yes install nginx
RUN apt-get --assume-yes build-dep libguestfs  
RUN apt-get --assume-yes install flex
RUN apt-get --assume-yes install bison
RUN DEBIAN_FRONTEND=noninteractive apt-get --assume-yes install linux-image-generic
RUN apt-get --assume-yes build-dep supermin  
RUN git clone https://github.com/libguestfs/supermin.git
RUN git clone https://github.com/anandramakrishna/libguestfs.git
WORKDIR /supermin
RUN ./bootstrap
RUN ./autogen.sh
RUN make install
WORKDIR /libguestfs
RUN ./autogen.sh
RUN make; rm po-docs/podfiles; make -C po-docs update-po
RUN make
RUN rm -v /etc/nginx/nginx.conf
ADD nginx.conf /etc/nginx/
ADD src/* /api/
EXPOSE 8080
CMD service nginx start && /api/index.py



