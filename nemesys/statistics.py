class Statistics:

  def __init__(self, packet_up_nem = 0, packet_up_oth = 0, packet_up_all = 0, packet_down_nem = 0, packet_down_oth = 0, packet_down_all = 0, packet_tot_nem = 0, packet_tot_oth = 0, packet_tot_all = 0, byte_up_nem = 0, byte_up_oth = 0, byte_up_all = 0, byte_down_nem = 0, byte_down_oth = 0, byte_down_all = 0, byte_tot_nem = 0, byte_tot_oth = 0, byte_tot_all = 0, payload_up_nem = 0, payload_up_oth = 0, payload_up_all = 0, payload_down_nem = 0, payload_down_oth = 0, payload_down_all = 0, payload_tot_nem = 0, payload_tot_oth = 0, payload_tot_all = 0, packet_up_nem_net = 0, packet_up_oth_net = 0, packet_up_all_net = 0, packet_down_nem_net = 0, packet_down_oth_net = 0, packet_down_all_net = 0, packet_tot_nem_net = 0, packet_tot_oth_net = 0, packet_tot_all_net = 0, byte_up_nem_net = 0, byte_up_oth_net = 0, byte_up_all_net = 0, byte_down_nem_net = 0, byte_down_oth_net = 0, byte_down_all_net = 0, byte_tot_nem_net = 0, byte_tot_oth_net = 0, byte_tot_all_net = 0, payload_up_nem_net = 0, payload_up_oth_net = 0, payload_up_all_net = 0, payload_down_nem_net = 0, payload_down_oth_net = 0, payload_down_all_net = 0, payload_tot_nem_net = 0, payload_tot_oth_net = 0, payload_tot_all_net = 0):

    self._packet_up_nem = packet_up_nem
    self._packet_up_oth = packet_up_oth
    self._packet_up_all = packet_up_all
    self._packet_down_nem = packet_down_nem
    self._packet_down_oth = packet_down_oth
    self._packet_down_all = packet_down_all
    self._packet_tot_nem = packet_tot_nem
    self._packet_tot_oth = packet_tot_oth
    self._packet_tot_all = packet_tot_all
    self._byte_up_nem = byte_up_nem
    self._byte_up_oth = byte_up_oth
    self._byte_up_all = byte_up_all
    self._byte_down_nem = byte_down_nem
    self._byte_down_oth = byte_down_oth
    self._byte_down_all = byte_down_all
    self._byte_tot_nem = byte_tot_nem
    self._byte_tot_oth = byte_tot_oth
    self._byte_tot_all = byte_tot_all
    self._payload_up_nem = payload_up_nem
    self._payload_up_oth = payload_up_oth
    self._payload_up_all = payload_up_all
    self._payload_down_nem = payload_down_nem
    self._payload_down_oth = payload_down_oth
    self._payload_down_all = payload_down_all
    self._payload_tot_nem = payload_tot_nem
    self._payload_tot_oth = payload_tot_oth
    self._payload_tot_all = payload_tot_all
    self._packet_up_nem_net = packet_up_nem_net
    self._packet_up_oth_net = packet_up_oth_net
    self._packet_up_all_net = packet_up_all_net
    self._packet_down_nem_net = packet_down_nem_net
    self._packet_down_oth_net = packet_down_oth_net
    self._packet_down_all_net = packet_down_all_net
    self._packet_tot_nem_net = packet_tot_nem_net
    self._packet_tot_oth_net = packet_tot_oth_net
    self._packet_tot_all_net = packet_tot_all_net
    self._byte_up_nem_net = byte_up_nem_net
    self._byte_up_oth_net = byte_up_oth_net
    self._byte_up_all_net = byte_up_all_net
    self._byte_down_nem_net = byte_down_nem_net
    self._byte_down_oth_net = byte_down_oth_net
    self._byte_down_all_net = byte_down_all_net
    self._byte_tot_nem_net = byte_tot_nem_net
    self._byte_tot_oth_net = byte_tot_oth_net
    self._byte_tot_all_net = byte_tot_all_net
    self._payload_up_nem_net = payload_up_nem_net
    self._payload_up_oth_net = payload_up_oth_net
    self._payload_up_all_net = payload_up_all_net
    self._payload_down_nem_net = payload_down_nem_net
    self._payload_down_oth_net = payload_down_oth_net
    self._payload_down_all_net = payload_down_all_net
    self._payload_tot_nem_net = payload_tot_nem_net
    self._payload_tot_oth_net = payload_tot_oth_net
    self._payload_tot_all_net = payload_tot_all_net

  @property
  def packet_up_nem(self):
    return self._packet_up_nem

  @property
  def packet_up_oth(self):
    return self._packet_up_oth

  @property
  def packet_up_all(self):
    return self._packet_up_all
  @property
  def packet_down_nem(self):
    return self._packet_down_nem

  @property
  def packet_down_oth(self):
    return self._packet_down_oth

  @property
  def packet_down_all(self):
    return self._packet_down_all

  @property
  def packet_tot_nem(self):
    return self._packet_tot_nem

  @property
  def packet_tot_oth(self):
    return self._packet_tot_oth

  @property
  def packet_tot_all(self):
    return self._packet_tot_all

  @property
  def byte_up_nem(self):
    return self._byte_up_nem

  @property
  def byte_up_oth(self):
    return self._byte_up_oth

  @property
  def byte_up_all(self):
    return self._byte_up_all

  @property
  def byte_down_nem(self):
    return self._byte_down_nem

  @property
  def byte_down_oth(self):
    return self._byte_down_oth

  @property
  def byte_down_all(self):
    return self._byte_down_all

  @property
  def byte_tot_nem(self):
    return self._byte_tot_nem

  @property
  def byte_tot_oth(self):
    return self._byte_tot_oth

  @property
  def byte_tot_all(self):
    return self._byte_tot_all

  @property
  def payload_up_nem(self):
    return self._payload_up_nem

  @property
  def payload_up_oth(self):
    return self._payload_up_oth

  @property
  def payload_up_all(self):
    return self._payload_up_all

  @property
  def payload_down_nem(self):
    return self._payload_down_nem

  @property
  def payload_down_oth(self):
    return self._payload_down_oth

  @property
  def payload_down_all(self):
    return self._payload_down_all

  @property
  def payload_tot_nem(self):
    return self._payload_tot_nem

  @property
  def payload_tot_oth(self):
    return self._payload_tot_oth

  @property
  def payload_tot_all(self):
    return self._payload_tot_all

  @property
  def packet_up_nem_net(self):
    return self._packet_up_nem_net

  @property
  def packet_up_oth_net(self):
    return self._packet_up_oth_net

  @property
  def packet_up_all_net(self):
    return self._packet_up_all_net

  @property
  def packet_down_nem_net(self):
    return self._packet_down_nem_net

  @property
  def packet_down_oth_net(self):
    return self._packet_down_oth_net

  @property
  def packet_down_all_net(self):
    return self._packet_down_all_net

  @property
  def packet_tot_nem_net(self):
    return self._packet_tot_nem_net

  @property
  def packet_tot_oth_net(self):
    return self._packet_tot_oth_net

  @property
  def packet_tot_all_net(self):
    return self._packet_tot_all_net

  @property
  def byte_up_nem_net(self):
    return self._byte_up_nem_net

  @property
  def byte_up_oth_net(self):
    return self._byte_up_oth_net

  @property
  def byte_up_all_net(self):
    return self._byte_up_all_net

  @property
  def byte_down_nem_net(self):
    return self._byte_down_nem_net

  @property
  def byte_down_oth_net(self):
    return self._byte_down_oth_net

  @property
  def byte_down_all_net(self):
    return self._byte_down_all_net

  @property
  def byte_tot_nem_net(self):
    return self._byte_tot_nem_net

  @property
  def byte_tot_oth_net(self):
    return self._byte_tot_oth_net

  @property
  def byte_tot_all_net(self):
    return self._byte_tot_all_net

  @property
  def payload_up_nem_net(self):
    return self._payload_up_nem_net

  @property
  def payload_up_oth_net(self):
    return self._payload_up_oth_net

  @property
  def payload_up_all_net(self):
    return self._payload_up_all_net

  @property
  def payload_down_nem_net(self):
    return self._payload_down_nem_net

  @property
  def payload_down_oth_net(self):
    return self._payload_down_oth_net

  @property
  def payload_down_all_net(self):
    return self._payload_down_all_net

  @property
  def payload_tot_nem_net(self):
    return self._payload_tot_nem_net

  @property
  def payload_tot_oth_net(self):
    return self._payload_tot_oth_net

  @property
  def payload_tot_all_net(self):
    return self._payload_tot_all_net

  def __str__(self):
    return "(byte) tot_all: %d; tot_all_net: %d; tot_nem: %d; tot_nem_net: %d; tot_oth: %d; tot_oth_net: %d; down_all: %d; down_all_net: %d; down_nem: %d; down_nem_net: %d; down_oth: %d; down_oth_net: %d; up_all: %d; up_all_net: %d; up_nem: %d; up_nem_net: %d; up_oth: %d; up_oth_net: %d" % (\
                  self.byte_tot_all, self.byte_tot_all_net, self.byte_tot_nem, self.byte_tot_nem_net, self.byte_tot_oth, self.byte_tot_oth_net, \
                  self.byte_down_all, self. byte_down_all_net, self.byte_down_nem, self.byte_down_nem_net, self.byte_down_oth, self.byte_down_oth_net, \
                  self.byte_up_all, self.byte_up_all_net, self.byte_up_nem, self.byte_up_nem_net, self.byte_up_oth, self.byte_up_oth_net)

if __name__ == '__main__':
  s = Statistics()
  print s
